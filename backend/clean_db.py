import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from app.services.chroma_client import ChromaHttpClient
from app.services.neo4j_rbac import RBACGraph

async def clean():
    chroma = ChromaHttpClient()
    try:
        chroma._client.delete_collection(name=chroma.collection_name)
        print("Chroma collection deleted.")
    except Exception as e:
        print(f"Chroma delete error: {e}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE embeddings, document_chunks, access_policies, documents, audit_logs CASCADE"))
        await db.commit()
    print("Postgres truncated.")
    
    graph = RBACGraph()
    async with graph._driver.session() as session:
        await session.run("MATCH (n:Document) DETACH DELETE n")
    print("Neo4j docs deleted.")

asyncio.run(clean())
