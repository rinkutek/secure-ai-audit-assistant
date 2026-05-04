from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import User, Role, UserRole, Document, AccessPolicy
from app.core.security import hash_password
from app.services.doc_ingest import ingest_document

SAMPLE_DOCS = [
    ("SOC 2 Evidence Retention Policy", "soc2_retention.txt", "SOC 2 evidence retention:\n- Retain evidence for at least 12 months after the audit period ends.\n- Evidence must be immutable or have tamper-evident controls.\n- Access to evidence repositories must be reviewed quarterly.\n- Exceptions require written approval by compliance leadership.\n"),
    ("PCI DSS Change Control Procedure", "pci_change_control.txt", "PCI DSS change control:\n- All changes to CDE systems must be documented and approved.\n- Emergency changes must be reviewed within 24 hours.\n- Maintain a change log with requestor, approver, and implementation details.\n"),
    ("Internal Incident Response Playbook", "incident_response.txt", "Incident response:\n- Triage and classify incidents within 30 minutes.\n- Preserve logs and forensic artifacts.\n- Notify stakeholders per severity matrix.\n- Conduct post-incident review within 10 business days.\n"),
]

async def seed_postgres():
    storage_dir = Path(settings.doc_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        for rn in ["admin","auditor","viewer"]:
            if not (await db.execute(select(Role).where(Role.name==rn))).scalar_one_or_none():
                db.add(Role(name=rn))
        await db.commit()
        roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}

        users = [
            ("admin@example.com", "AdminPass123!", ["admin","auditor"]),
            ("auditor@example.com", "AuditorPass123!", ["auditor"]),
            ("viewer@example.com", "ViewerPass123!", ["viewer"]),
        ]
        created={}
        for email,pw,rns in users:
            u = (await db.execute(select(User).where(User.email==email))).scalar_one_or_none()
            if not u:
                u = User(email=email, password_hash=hash_password(pw), is_active=True)
                db.add(u); await db.flush()
                for rn in rns:
                    db.add(UserRole(user_id=u.id, role_id=roles[rn].id))
                await db.commit()
            created[email]=u.id

        doc_ids=[]
        for title, filename, text in SAMPLE_DOCS:
            p = storage_dir / filename
            p.write_text(text, encoding="utf-8")
            existing = (await db.execute(select(Document).where(Document.filename==filename))).scalar_one_or_none()
            if existing:
                doc_ids.append(existing.id); continue
            doc_id,_ = await ingest_document(db, title=title, filename=filename, storage_path=str(p), content_text=text)
            await db.commit()
            doc_ids.append(doc_id)

        policies = [
            ("auditor", doc_ids[0], "READ"),
            ("auditor", doc_ids[1], "READ"),
            ("viewer", doc_ids[2], "READ"),
            ("admin", doc_ids[0], "READ"),
            ("admin", doc_ids[1], "READ"),
            ("admin", doc_ids[2], "READ"),
        ]
        for role_name, doc_id, perm in policies:
            exists = (await db.execute(select(AccessPolicy).where(AccessPolicy.role_name==role_name, AccessPolicy.doc_id==doc_id, AccessPolicy.permission==perm))).scalar_one_or_none()
            if not exists:
                db.add(AccessPolicy(role_name=role_name, doc_id=doc_id, permission=perm))
        await db.commit()

    return created, doc_ids

async def seed_neo4j(users, doc_ids):
    driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
        for did in doc_ids:
            await session.run("MERGE (:Document {id:$id})", id=did)
        for rn in ["admin","auditor","viewer"]:
            await session.run("MERGE (:Role {name:$name})", name=rn)
        for email, uid in users.items():
            await session.run("MERGE (:User {id:$id, email:$email})", id=uid, email=email)

        await session.run("MATCH (u:User {email:'admin@example.com'}),(r:Role {name:'admin'}) MERGE (u)-[:HAS_ROLE]->(r)")
        await session.run("MATCH (u:User {email:'admin@example.com'}),(r:Role {name:'auditor'}) MERGE (u)-[:HAS_ROLE]->(r)")
        await session.run("MATCH (u:User {email:'auditor@example.com'}),(r:Role {name:'auditor'}) MERGE (u)-[:HAS_ROLE]->(r)")
        await session.run("MATCH (u:User {email:'viewer@example.com'}),(r:Role {name:'viewer'}) MERGE (u)-[:HAS_ROLE]->(r)")

        await session.run("MATCH (r:Role {name:'auditor'}),(d:Document {id:$d}) MERGE (r)-[:CAN_ACCESS {permission:'READ'}]->(d)", d=doc_ids[0])
        await session.run("MATCH (r:Role {name:'auditor'}),(d:Document {id:$d}) MERGE (r)-[:CAN_ACCESS {permission:'READ'}]->(d)", d=doc_ids[1])
        await session.run("MATCH (r:Role {name:'viewer'}),(d:Document {id:$d}) MERGE (r)-[:CAN_ACCESS {permission:'READ'}]->(d)", d=doc_ids[2])
        for did in doc_ids:
            await session.run("MATCH (r:Role {name:'admin'}),(d:Document {id:$d}) MERGE (r)-[:CAN_ACCESS {permission:'READ'}]->(d)", d=did)
    await driver.close()

async def wait_for_services():
    import urllib.request
    
    def log(msg):
        print(msg, file=sys.stderr, flush=True)

    log("🔍 Starting robust service health checks...")
    
    # Wait for ChromaDB (HTTP check)
    url = settings.chroma_http_url.rstrip("/")
    log(f"🌐 Checking ChromaDB at {url}...")
    
    for i in range(20):
        try:
            # We check the heartbeat or version endpoint
            with urllib.request.urlopen(f"{url}/api/v1/heartbeat", timeout=2) as response:
                if response.status == 200:
                    log("✅ ChromaDB is healthy and responding.")
                    break
        except Exception as e:
            log(f"⏳ Waiting for ChromaDB... (Attempt {i+1}/20) - Error: {e}")
            await asyncio.sleep(5)
    else:
        log("❌ ChromaDB failed to become healthy in time.")
        sys.exit(1)

    # Wait for Neo4j (Driver check)
    log(f"🌐 Checking Neo4j at {settings.neo4j_uri}...")
    for i in range(20):
        try:
            driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
            await driver.verify_connectivity()
            await driver.close()
            log("✅ Neo4j is healthy.")
            break
        except Exception as e:
            log(f"⏳ Waiting for Neo4j... (Attempt {i+1}/20) - Error: {e}")
            await asyncio.sleep(5)
    else:
        log("❌ Neo4j failed to become healthy in time.")
        sys.exit(1)

async def main():
    await wait_for_services()
    users, doc_ids = await seed_postgres()
    await seed_neo4j(users, doc_ids)
    print("Seed complete.", file=sys.stderr, flush=True)
    print("Login users:")
    print(" admin@example.com / AdminPass123!")
    print(" auditor@example.com / AuditorPass123!")
    print(" viewer@example.com / ViewerPass123!")

if __name__ == "__main__":
    asyncio.run(main())
