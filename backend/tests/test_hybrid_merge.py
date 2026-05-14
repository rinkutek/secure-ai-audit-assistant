from app.services.retrieval import hybrid_merge_rerank

def test_hybrid_merge_contains_union():
    sem=[{"chunk_id":"c1","doc_id":"d1","chunk_index":0,"content":"a","distance":0.1}]
    kw=[{"chunk_id":"c2","doc_id":"d2","chunk_index":0,"content":"b","score":10.0}]
    out = hybrid_merge_rerank(semantic=sem, keyword=kw, alpha=0.5, top_k=10)
    assert {r["chunk_id"] for r in out} == {"c1","c2"}

def test_hybrid_merge_ranking():
    sem=[
        {"chunk_id":"c1","distance":0.1}, # Very close semantically
        {"chunk_id":"c2","distance":0.9}  # Far semantically
    ]
    kw=[
        {"chunk_id":"c1","score":1.0}, # Low keyword score
        {"chunk_id":"c2","score":10.0} # High keyword score
    ]
    # With alpha=0.9, semantic dominates. c1 should be first
    out = hybrid_merge_rerank(semantic=sem, keyword=kw, alpha=0.9, top_k=10)
    assert out[0]["chunk_id"] == "c1"

    # With alpha=0.1, keyword dominates. c2 should be first
    out2 = hybrid_merge_rerank(semantic=sem, keyword=kw, alpha=0.1, top_k=10)
    assert out2[0]["chunk_id"] == "c2"

def test_hybrid_merge_empty():
    assert hybrid_merge_rerank(semantic=[], keyword=[], alpha=0.5, top_k=10) == []
