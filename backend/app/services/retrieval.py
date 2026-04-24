from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from rank_bm25 import BM25Okapi
from app.db.models import DocumentChunk, Document
from app.core.config import settings

def _tokenize(text: str) -> List[str]:
    return [t for t in "".join([c.lower() if c.isalnum() else " " for c in text]).split() if t]

def _minmax(scores: List[float]) -> List[float]:
    if not scores: return []
    mn, mx = min(scores), max(scores)
    if mx-mn < 1e-9: return [0.0 for _ in scores]
    return [(s-mn)/(mx-mn) for s in scores]

async def bm25_keyword_search(session: AsyncSession, *, query: str, top_k: int) -> List[Dict[str, Any]]:
    res = await session.execute(select(DocumentChunk.id, DocumentChunk.doc_id, DocumentChunk.chunk_index, DocumentChunk.content))
    rows = res.all()
    if not rows:
        return []
    corpus = [r[3] for r in rows]
    bm25 = BM25Okapi([_tokenize(t) for t in corpus])
    scores = bm25.get_scores(_tokenize(query))
    idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    out=[]
    for i in idxs:
        out.append({"chunk_id": rows[i][0], "doc_id": rows[i][1], "chunk_index": rows[i][2], "content": rows[i][3], "score": float(scores[i]), "source":"bm25"})
    return out

def hybrid_merge_rerank(*, semantic: List[Dict[str, Any]], keyword: List[Dict[str, Any]], alpha: float, top_k: int) -> List[Dict[str, Any]]:
    sem_sim=[1.0/(1.0+float(r.get("distance",1.0))) for r in semantic]
    sem_n=_minmax(sem_sim)
    kw_raw = [float(r.get("score", 0.0)) for r in keyword]
    kw_n=_minmax(kw_raw)

    merged={}
    for i,r in enumerate(semantic):
        cid=r["chunk_id"]
        merged[cid]={**r,"sem_norm":sem_n[i],"kw_norm":0.0}
    for i,r in enumerate(keyword):
        cid=r["chunk_id"]
        if cid not in merged:
            merged[cid]={**r,"sem_norm":0.0,"kw_norm":kw_n[i]}
        else:
            merged[cid]["kw_norm"]=max(merged[cid]["kw_norm"], kw_n[i])

    out=[]
    for r in merged.values():
        r["hybrid_score"]=alpha*r["sem_norm"]+(1-alpha)*r["kw_norm"]
        out.append(r)
    out.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return out[:top_k]

async def attach_document_metadata(session: AsyncSession, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chunks: return chunks
    doc_ids=sorted({c["doc_id"] for c in chunks if c.get("doc_id")})
    res=await session.execute(select(Document.id, Document.title, Document.filename).where(Document.id.in_(doc_ids)))
    meta={r[0]: {"title": r[1], "filename": r[2]} for r in res.all()}
    for c in chunks:
        c.update(meta.get(c["doc_id"], {}))
    return chunks
