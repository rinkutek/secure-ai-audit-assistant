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
                cypher = '''
                MATCH (n)-[r]->(m)
                RETURN 
                  id(n) as source_id, labels(n)[0] as source_label, properties(n) as source_props,
                  type(r) as rel_type, properties(r) as rel_props,
                  id(m) as target_id, labels(m)[0] as target_label, properties(m) as target_props
                '''
                res = await session.run(cypher)
                nodes = {}
                links = []
                async for record in res:
                    sid = f"{record['source_label']}_{record['source_id']}"
                    tid = f"{record['target_label']}_{record['target_id']}"
                    
                    if sid not in nodes:
                        s_props = dict(record['source_props'])
                        if 'id' in s_props:
                            s_props['app_id'] = s_props.pop('id')
                        nodes[sid] = {"id": sid, "label": record['source_label'], "type": record['source_label'], **s_props}
                        
                    if tid not in nodes:
                        t_props = dict(record['target_props'])
                        if 'id' in t_props:
                            t_props['app_id'] = t_props.pop('id')
                        nodes[tid] = {"id": tid, "label": record['target_label'], "type": record['target_label'], **t_props}
                        
                    links.append({
                        "source": sid,
                        "target": tid,
                        "label": record['rel_type'],
                        **record['rel_props']
                    })
                
                # Deduplicate links if needed, but above will just grab all relationships
                return {"nodes": list(nodes.values()), "links": links}
        except Exception:
            raise AppError("RBAC service unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="RBAC_UNAVAILABLE")

    async def add_document(self, doc_id: str):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (:Document {id:$id})", id=doc_id)
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

    async def add_policy(self, role_name: str, doc_id: str, permission: str):
        try:
            async with self._driver.session() as session:
                await session.run("MERGE (:Role {name:$name})", name=role_name)
                await session.run("MERGE (:Document {id:$id})", id=doc_id)
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
