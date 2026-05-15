import asyncio
from app.services.neo4j_rbac import RBACGraph

async def run_diag():
    g = RBACGraph()
    async with g._driver.session() as s:
        u = await s.run('MATCH (n:User) RETURN count(n)')
        r = await s.run('MATCH (n:Role) RETURN count(n)')
        d = await s.run('MATCH (n:Document) RETURN count(n)')
        p = await s.run('MATCH ()-[r:CAN_ACCESS]->() RETURN count(r)')
        
        u_count = await u.single()
        r_count = await r.single()
        d_count = await d.single()
        p_count = await p.single()
        
        print("\n--- GRAPH DIAGNOSTICS ---")
        print(f"Users: {u_count[0]}")
        print(f"Roles: {r_count[0]}")
        print(f"Documents: {d_count[0]}")
        print(f"Permission Links: {p_count[0]}")
        print("--------------------------\n")
    await g._driver.close()

if __name__ == "__main__":
    asyncio.run(run_diag())
