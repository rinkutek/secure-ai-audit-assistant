from app.services.audit_log import compute_hash, canonical_json

def test_hash_chain_deterministic():
    prev="0"*64
    payload={"timestamp_utc":"2026-01-01T00:00:00+00:00","user_id":"u1","action":"QUERY","outcome":"ALLOW","resource_ids":["d1"],"client_ip":"127.0.0.1","roles":["auditor"]}
    assert compute_hash(prev,payload)==compute_hash(prev,payload)

def test_canonical_json_sorting():
    obj1 = {"b": 2, "a": 1}
    obj2 = {"a": 1, "b": 2}
    assert canonical_json(obj1) == canonical_json(obj2)

def test_hash_chaining():
    prev1 = "0"*64
    payload1 = {"a": 1}
    hash1 = compute_hash(prev1, payload1)
    
    payload2 = {"b": 2}
    hash2 = compute_hash(hash1, payload2)
    
    assert hash1 != hash2
    assert hash1 != "0"*64
