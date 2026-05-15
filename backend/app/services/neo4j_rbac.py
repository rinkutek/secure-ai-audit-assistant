from typing import List
from neo4j import AsyncGraphDatabase
from cachetools import TTLCache
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from app.core.config import settings
from app.core.exceptions import AppError

_cache = TTLCache(maxsize=10_000, ttl=settings.rbac_cache_ttl_seconds)

class RBACGraph:
    def __init__(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

    async def allowed_doc_ids(self, *, user_id: str, roles: List[str]) -> List[str]:
        cache_key = f"{user_id}:{'|'.join(sorted(roles))}"
        if cache_key in _cache:
            return _cache[cache_key]
        try:
            async with self._driver.session() as session:
                cypher = '''
                MATCH (u:User {id: $user_id})-[:HAS_ROLE]->(r:Role)-[:CAN_ACCESS {permission:'READ'}]->(d:Document)
                RETURN DISTINCT d.id AS doc_id
                '''
                res = await session.run(cypher, user_id=user_id)
                doc_ids = [r["doc_id"] async for r in res]
        except Exception:
            raise AppError("RBAC service unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="RBAC_UNAVAILABLE")
        _cache[cache_key] = doc_ids
        return doc_ids

    async def get_full_graph(self) -> dict:
        try:
            async with self._driver.session() as session:
                # 1. Fetch all nodes
                node_res = await session.run("MATCH (n) RETURN id(n) as id, labels(n)[0] as label, properties(n) as props")
                nodes = []
                for record in await node_res.data():
                    nid = f"{record['label']}_{record['id']}"
                    props = dict(record['props'])
                    if 'id' in props:
                        props['app_id'] = props.pop('id')
                    node_data = {"id": nid, "label": record['label'], "type": record['label'], **props}
                    print(f"DEBUG: Neo4j Node {nid}: {node_data}")
                    nodes.append(node_data)
                
                # 2. Fetch all relationships
                rel_res = await session.run("MATCH (n)-[r]->(m) RETURN id(n) as sid, labels(n)[0] as slabel, id(m) as tid, labels(m)[0] as tlabel, type(r) as type, properties(r) as props")
                links = []
                for record in await rel_res.data():
                    links.append({
                        "source": f"{record['slabel']}_{record['sid']}",
                        "target": f"{record['tlabel']}_{record['tid']}",
                        "label": record['type'],
                        **record['props']
                    })
                
                return {"nodes": nodes, "links": links}
        except Exception as e:
            print(f"Graph error: {e}")
            raise AppError("RBAC service unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="RBAC_UNAVAILABLE")

    async def add_document(self, doc_id: str, title: str = "Untitled"):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (d:Document {id:$id}) SET d.title = $title", id=doc_id, title=title)
        except Exception as e:
            print(f"Neo4j doc error: {e}")

    async def add_role(self, role_name: str):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (:Role {name:$name})", name=role_name)
        except Exception as e:
            print(f"Neo4j role error: {e}")

    async def add_user(self, user_id: str, email: str, roles: List[str]):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (:User {id:$id, email:$email})", id=user_id, email=email)
                for r in roles:
                    await session.run("MERGE (:Role {name:$name})", name=r)
                    await session.run("MATCH (u:User {id:$id}),(r:Role {name:$name}) MERGE (u)-[:HAS_ROLE]->(r)", id=user_id, name=r)
        except Exception as e:
            print(f"Neo4j user error: {e}")

    async def remove_user(self, user_id: str):
        try:
            async with self._driver.session() as session:
                await session.run("MATCH (u:User {id:$id}) DETACH DELETE u", id=user_id)
        except Exception as e:
            print(f"Neo4j remove user error: {e}")

    async def update_user_roles(self, user_id: str, email: str, roles: List[str]):
        try:
            async with self._driver.session() as session:
                # Clear existing roles
                await session.run("MATCH (u:User {id:$id})-[rel:HAS_ROLE]->() DELETE rel", id=user_id)
                # Re-add specified roles
                for r in roles:
                    await session.run("MERGE (:Role {name:$name})", name=r)
                    await session.run("MATCH (u:User {id:$id}),(r:Role {name:$name}) MERGE (u)-[:HAS_ROLE]->(r)", id=user_id, name=r)
        except Exception as e:
            print(f"Neo4j update user roles error: {e}")

    async def add_policy(self, role_name: str, doc_id: str, permission: str, doc_title: str = "Untitled"):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (:Role {name:$name})", name=role_name)
                await session.run("MERGE (d:Document {id:$id}) SET d.title = $title", id=doc_id, title=doc_title)
                await session.run("MATCH (r:Role {name:$name}),(d:Document {id:$id}) MERGE (r)-[:CAN_ACCESS {permission:$perm}]->(d)", name=role_name, id=doc_id, perm=permission)
        except Exception as e:
            print(f"Neo4j policy error: {e}")

    async def update_policy_permission(self, role_name: str, doc_id: str, permission: str):
        try:
            async with self._driver.session() as session:
                await session.run("MATCH (r:Role {name:$name})-[rel:CAN_ACCESS]->(d:Document {id:$id}) SET rel.permission=$perm", name=role_name, id=doc_id, perm=permission)
        except Exception as e:
            print(f"Neo4j policy update error: {e}")

    async def remove_document(self, doc_id: str):
        try:
            async with self._driver.session() as session:
                await session.run("MATCH (d:Document {id:$id}) DETACH DELETE d", id=doc_id)
        except Exception as e:
            print(f"Neo4j doc remove error: {e}")
