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

def test_tamper_detection():
    # Simulate an audit log chain
    chain = []
    prev = "0"*64
    for i in range(5):
        payload = {"action": "QUERY", "id": i}
        h = compute_hash(prev, payload)
        chain.append({"payload": payload, "prev_hash": prev, "hash": h})
        prev = h

    # Validate chain is intact
    for i in range(1, 5):
        assert chain[i]["prev_hash"] == chain[i-1]["hash"]
        assert compute_hash(chain[i]["prev_hash"], chain[i]["payload"]) == chain[i]["hash"]

    # Maliciously alter payload #2
    chain[2]["payload"]["action"] = "DOWNLOAD"

    # Validation must now fail for block #2
    tampered_hash = compute_hash(chain[2]["prev_hash"], chain[2]["payload"])
    assert tampered_hash != chain[2]["hash"], "Tampered block must produce a different hash!"
