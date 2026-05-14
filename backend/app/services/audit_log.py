from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib
import orjson
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from app.db.models import AuditLog
from app.core.exceptions import AppError

def canonical_json(obj: Dict[str, Any]) -> str:
    return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS).decode("utf-8")

def compute_hash(hash_prev: str, payload: Dict[str, Any]) -> str:
    msg = (hash_prev + canonical_json(payload)).encode("utf-8")
    return hashlib.sha256(msg).hexdigest()

async def _last_hash(session: AsyncSession) -> str:
    r = await session.execute(select(AuditLog.hash_curr).order_by(AuditLog.log_id.desc()).limit(1))
    row = r.first()
    return row[0] if row else "0"*64

async def write_audit_log(session: AsyncSession, *, user_id: str, action: str, outcome: str, resource_ids: List[str], client_ip: str, roles: List[str]) -> AuditLog:
    try:
        prev = await _last_hash(session)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        payload = {
            "timestamp_utc": now.isoformat(),
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "resource_ids": resource_ids,
            "client_ip": client_ip,
            "roles": roles,
        }
        curr = compute_hash(prev, payload)
        row = AuditLog(
            timestamp_utc=now,
            user_id=user_id,
            action=action,
            outcome=outcome,
            resource_ids=orjson.dumps(resource_ids).decode(),
            client_ip=client_ip,
            roles=orjson.dumps(roles).decode(),
            hash_prev=prev,
            hash_curr=curr,
        )
        session.add(row)
        await session.flush()
        return row
    except Exception:
        raise AppError("Audit logging unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="AUDIT_LOG_WRITE_FAILED")

async def verify_audit_log_chain(session: AsyncSession) -> Dict[str, Any]:
    res = await session.execute(select(AuditLog).order_by(AuditLog.log_id.asc()))
    logs = list(res.scalars().all())
    prev = "0"*64
    for log in logs:
        payload = {
            "timestamp_utc": log.timestamp_utc.astimezone(timezone.utc).isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "outcome": log.outcome,
            "resource_ids": orjson.loads(log.resource_ids),
            "client_ip": log.client_ip,
            "roles": orjson.loads(log.roles),
        }
        exp = compute_hash(prev, payload)
        if log.hash_prev != prev:
            return {"ok": False, "checked": log.log_id-1, "mismatch_at_log_id": log.log_id, "reason": "hash_prev mismatch"}
        if log.hash_curr != exp:
            return {"ok": False, "checked": log.log_id-1, "mismatch_at_log_id": log.log_id, "reason": "hash_curr mismatch"}
        prev = log.hash_curr
    return {"ok": True, "checked": len(logs), "mismatch_at_log_id": None, "reason": None}
