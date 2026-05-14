import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.db.models import AuditLog
from app.services.audit_log import compute_hash
import orjson
from datetime import timezone

async def fix():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(AuditLog).order_by(AuditLog.log_id.asc()))
        logs = res.scalars().all()
        prev = "0"*64
        for log in logs:
            # We must zero microseconds because we fixed the code to do that moving forward, 
            # and existing logs probably had nonzero but we can't recover the exact str. 
            # Best is to adopt their DB timestamp with 0 microsecond so they match.
            ts = log.timestamp_utc.astimezone(timezone.utc).replace(microsecond=0)
            log.timestamp_utc = ts
            payload = {
                "timestamp_utc": ts.isoformat(),
                "user_id": log.user_id,
                "action": log.action,
                "outcome": log.outcome,
                "resource_ids": orjson.loads(log.resource_ids),
                "client_ip": log.client_ip,
                "roles": orjson.loads(log.roles),
            }
            curr = compute_hash(prev, payload)
            log.hash_prev = prev
            log.hash_curr = curr
            prev = curr
        await db.commit()
    print("Hashes repaired.")

asyncio.run(fix())
