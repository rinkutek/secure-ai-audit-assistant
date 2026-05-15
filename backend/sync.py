import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.db.models import User, Role, AccessPolicy, Document, UserRole
from app.services.neo4j_rbac import RBACGraph

async def sync():
    graph = RBACGraph()
    async with AsyncSessionLocal() as db:
        docs = (await db.execute(select(Document))).scalars().all()
        for d in docs: await graph.add_document(d.id)
        
        roles = (await db.execute(select(Role))).scalars().all()
        for r in roles: await graph.add_role(r.name)
        
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            user_roles = (await db.execute(select(Role.name).join(UserRole).where(UserRole.user_id==u.id))).scalars().all()
            await graph.add_user(str(u.id), u.email, user_roles)
            
        pols = (await db.execute(select(AccessPolicy))).scalars().all()
        for p in pols: await graph.add_policy(p.role_name, p.doc_id, p.permission)

if __name__ == "__main__":
    asyncio.run(sync())
