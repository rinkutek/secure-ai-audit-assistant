from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_404_NOT_FOUND
from app.api.deps import get_db, require_admin
from app.core.security import hash_password
from app.core.exceptions import AppError
from app.db.models import User, Role, UserRole, AccessPolicy, Document
from app.schemas.admin import UserCreate, UserOut, UserUpdateRoles, RoleCreate, RoleOut, PolicyCreate, PolicyOut, GraphData
from app.services.audit_log import write_audit_log
from app.services.neo4j_rbac import RBACGraph

router = APIRouter(prefix="/admin")

@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    users = (await db.execute(select(User).options(selectinload(User.roles)))).scalars().all()
    return [UserOut(id=u.id, email=u.email, roles=[r.name for r in u.roles], is_active=u.is_active) for u in users]

@router.get("/graph", response_model=GraphData)
async def get_rbac_graph(admin=Depends(require_admin)):
    return await RBACGraph().get_full_graph()

@router.post("/users", response_model=UserOut)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    if (await db.execute(select(User).where(User.email==payload.email))).scalar_one_or_none():
        raise AppError("Email already exists", status_code=409, code="ALREADY_EXISTS")
    u = User(email=payload.email, password_hash=hash_password(payload.password), is_active=True)
    db.add(u); await db.flush()
    role_names=[]
    for rn in payload.roles:
        r = (await db.execute(select(Role).where(Role.name==rn))).scalar_one_or_none()
        if not r:
            r = Role(name=rn); db.add(r); await db.flush()
        db.add(UserRole(user_id=u.id, role_id=r.id))
        role_names.append(rn)
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_CREATE_USER", outcome="ALLOW", resource_ids=[u.id], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    
    await RBACGraph().add_user(user_id=str(u.id), email=u.email, roles=role_names)
    
    return UserOut(id=u.id, email=u.email, roles=role_names, is_active=u.is_active)

@router.put("/users/{user_id}/roles", response_model=UserOut)
async def update_user_roles(user_id: str, payload: UserUpdateRoles, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    u = (await db.execute(select(User).options(selectinload(User.roles)).where(User.id==user_id))).scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=HTTP_404_NOT_FOUND, code="NOT_FOUND")
    
    await db.execute(delete(UserRole).where(UserRole.user_id==user_id))
    
    role_names = []
    for rn in payload.roles:
        r = (await db.execute(select(Role).where(Role.name==rn))).scalar_one_or_none()
        if not r:
            r = Role(name=rn); db.add(r); await db.flush()
        db.add(UserRole(user_id=u.id, role_id=r.id))
        role_names.append(rn)
        
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_UPDATE_USER_ROLES", outcome="ALLOW", resource_ids=[user_id] + role_names, client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    
    await RBACGraph().update_user_roles(user_id=str(u.id), email=u.email, roles=role_names)
    
    return UserOut(id=u.id, email=u.email, roles=role_names, is_active=u.is_active)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    u = (await db.execute(select(User).where(User.id==user_id))).scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=HTTP_404_NOT_FOUND, code="NOT_FOUND")
    await db.execute(delete(User).where(User.id==user_id))
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_DELETE_USER", outcome="ALLOW", resource_ids=[user_id], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    await RBACGraph().remove_user(user_id=user_id)
    return {"ok": True}

@router.get("/roles", response_model=list[RoleOut])
async def list_roles(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    roles = (await db.execute(select(Role))).scalars().all()
    return [RoleOut(id=r.id, name=r.name) for r in roles]

@router.post("/roles", response_model=RoleOut)
async def create_role(payload: RoleCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    r = (await db.execute(select(Role).where(Role.name==payload.name))).scalar_one_or_none()
    if r:
        return RoleOut(id=r.id, name=r.name)
    r = Role(name=payload.name); db.add(r); await db.flush()
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_CREATE_ROLE", outcome="ALLOW", resource_ids=[payload.name], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    
    await RBACGraph().add_role(role_name=r.name)
    
    return RoleOut(id=r.id, name=r.name)

@router.get("/policies", response_model=list[PolicyOut])
async def list_policies(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    pols = (await db.execute(select(AccessPolicy))).scalars().all()
    return [PolicyOut(id=p.id, role_name=p.role_name, doc_id=p.doc_id, permission=p.permission) for p in pols]

@router.post("/policies", response_model=PolicyOut)
async def create_policy(payload: PolicyCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    existing = (await db.execute(select(AccessPolicy).where(
        AccessPolicy.role_name == payload.role_name,
        AccessPolicy.doc_id == payload.doc_id,
        AccessPolicy.permission == payload.permission
    ))).scalar_one_or_none()
    
    if existing:
        raise AppError("Policy already exists", status_code=409, code="ALREADY_EXISTS")

    p = AccessPolicy(role_name=payload.role_name, doc_id=payload.doc_id, permission=payload.permission)
    db.add(p); await db.flush()
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_CREATE_POLICY", outcome="ALLOW", resource_ids=[payload.doc_id], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    
    # Get doc title for Neo4j
    doc = (await db.execute(select(Document).where(Document.id == p.doc_id))).scalar_one_or_none()
    doc_title = doc.title if doc else "Untitled"
    await RBACGraph().add_policy(role_name=p.role_name, doc_id=p.doc_id, permission=p.permission, doc_title=doc_title)
    
    return PolicyOut(id=p.id, role_name=p.role_name, doc_id=p.doc_id, permission=p.permission)

@router.put("/policies/{policy_id}/toggle", response_model=PolicyOut)
async def toggle_policy(policy_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    p = (await db.execute(select(AccessPolicy).where(AccessPolicy.id==policy_id))).scalar_one_or_none()
    if not p:
        raise AppError("Policy not found", status_code=HTTP_404_NOT_FOUND, code="NOT_FOUND")
    
    new_perm = "REVOKED" if p.permission == "READ" else "READ"
    p.permission = new_perm
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_TOGGLE_POLICY", outcome="ALLOW", resource_ids=[policy_id], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    
    await RBACGraph().update_policy_permission(role_name=p.role_name, doc_id=p.doc_id, permission=new_perm)
    
    return PolicyOut(id=p.id, role_name=p.role_name, doc_id=p.doc_id, permission=p.permission)

@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    p = (await db.execute(select(AccessPolicy).where(AccessPolicy.id==policy_id))).scalar_one_or_none()
    if not p:
        raise AppError("Policy not found", status_code=HTTP_404_NOT_FOUND, code="NOT_FOUND")
    await db.execute(delete(AccessPolicy).where(AccessPolicy.id==policy_id))
    await write_audit_log(db, user_id=admin["user_id"], action="ADMIN_DELETE_POLICY", outcome="ALLOW", resource_ids=[policy_id], client_ip="local", roles=admin.get("roles", []))
    await db.commit()
    return {"ok": True}

