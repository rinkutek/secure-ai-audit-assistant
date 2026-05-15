import orjson
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE, HTTP_404_NOT_FOUND
from app.api.deps import get_current_user, get_client_ip
from app.core.config import settings
from app.core.normalize import normalize_query
from app.core.exceptions import AppError
from app.db.session import get_db
from app.db.models import ChatSession, ChatMessage
from app.schemas.query import QueryRequest, QueryResponse, Citation, QueryDebug
from app.services.embeddings import get_embedding_provider
from app.services.chroma_client import ChromaHttpClient
from app.services.retrieval import bm25_keyword_search, hybrid_merge_rerank, attach_document_metadata
from app.services.neo4j_rbac import RBACGraph
from app.services.llm import get_llm_provider
from app.services.audit_log import write_audit_log

router = APIRouter()

@router.post("/chat/session")
async def create_chat_session(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = ChatSession(user_id=user["user_id"], title="New Chat")
    db.add(s)
    await db.commit()
    return {"session_id": s.id}

@router.get("/chat/sessions")
async def get_chat_sessions(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    res = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user["user_id"])
        .order_by(ChatSession.created_at.desc())
        .limit(50)
    )
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in res.scalars().all()]

@router.get("/chat/session/{session_id}")
async def get_chat_session(session_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    sess = (await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user["user_id"]))).scalar_one_or_none()
    if not sess: raise AppError("Not found", HTTP_404_NOT_FOUND)
    res = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()))
    msgs = []
    for m in res.scalars().all():
        try:
            cits = orjson.loads(m.citations)
        except:
            cits = []
        msgs.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": cits,
            "created_at": m.created_at.isoformat()
        })
    return {"id": sess.id, "title": sess.title, "messages": msgs}

from pydantic import BaseModel
class RenameSessionRequest(BaseModel):
    title: str

@router.put("/chat/session/{session_id}")
async def rename_chat_session(session_id: str, req: RenameSessionRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    sess = (await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user["user_id"]))).scalar_one_or_none()
    if not sess: raise AppError("Not found", HTTP_404_NOT_FOUND)
    sess.title = req.title[:255]
    await db.commit()
    return {"ok": True}

@router.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    sess = (await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user["user_id"]))).scalar_one_or_none()
    if not sess: raise AppError("Not found", HTTP_404_NOT_FOUND)
    await db.delete(sess)
    await db.commit()
    return {"ok": True}

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest, request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), client_ip: str = Depends(get_client_ip)) -> QueryResponse:
    user_id = user["user_id"]
    roles = user.get("roles", [])

    if len(req.query) > settings.max_query_chars:
        raise AppError("Query too long", status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, code="QUERY_TOO_LONG")

    session_id = req.session_id
    if not session_id:
        sess = ChatSession(user_id=user_id, title=req.query[:40] + ("..." if len(req.query)>40 else ""))
        db.add(sess)
        await db.flush()
        session_id = sess.id

    q = normalize_query(req.query)

    embedder = get_embedding_provider()
    qvec = (await embedder.embed([q]))[0]

    chroma = ChromaHttpClient()
    semantic_raw = await chroma.query(query_embeddings=[qvec], n_results=settings.rag_top_k)
    semantic=[]
    for r in semantic_raw:
        md = r.get("metadata") or {}
        semantic.append({
            "chunk_id": md.get("chunk_id") or r["id"],
            "doc_id": md.get("doc_id"),
            "chunk_index": md.get("chunk_index", 0),
            "content": r.get("document") or "",
            "distance": r.get("distance", 1.0),
            "source": "chroma",
        })

    keyword = await bm25_keyword_search(db, query=q, top_k=settings.rag_keyword_top_k)

    merged = hybrid_merge_rerank(
        semantic=semantic,
        keyword=keyword,
        alpha=settings.hybrid_alpha,
        top_k=max(settings.rag_top_k, settings.rag_keyword_top_k),
    )
    retrieved_total = len(merged)

    allowed = set(await RBACGraph().allowed_doc_ids(user_id=user_id, roles=roles))
    authorized = [c for c in merged if c.get("doc_id") in allowed]

    if not authorized:
        await write_audit_log(
            db, user_id=user_id, action="QUERY", outcome="DENY",
            resource_ids=sorted({c.get("doc_id") or "unknown" for c in merged})[:50],
            client_ip=client_ip, roles=roles
        )
        db.add(ChatMessage(session_id=session_id, role="user", content=q))
        db.add(ChatMessage(session_id=session_id, role="assistant", content="No results (insufficient access)"))
        await db.commit()
        return QueryResponse(
            answer="No results (insufficient access)",
            citations=[],
            debug=QueryDebug(retrieved_total=retrieved_total, authorized_total=0),
            session_id=session_id
        )

    authorized = await attach_document_metadata(db, authorized)

    ctx=[]; citations=[]
    for c in authorized[:settings.rag_top_k]:
        cit = f"DOC:{c['doc_id']}#{c.get('chunk_index',0)}"
        ctx.append({"content": c["content"], "citation": cit})
        citations.append(Citation(doc_id=c["doc_id"], chunk_id=c["chunk_id"], title=c.get("title"), filename=c.get("filename"), chunk_index=c.get("chunk_index")))

    # Fetch past messages
    past_msgs_raw = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()))
    past_messages = [{"role": m.role, "content": m.content} for m in past_msgs_raw.scalars().all()]

    answer = await get_llm_provider().answer(question=q, context_chunks=ctx, past_messages=past_messages)

    import re
    cited_doc_ids = set(re.findall(r"\[DOC:([0-9a-fA-F-]+)(?:#\d+)?\]", answer))
    
    unique_citations = []
    seen_docs = set()
    filter_set = cited_doc_ids
    
    for c in citations:
        if c.doc_id in filter_set and c.doc_id not in seen_docs:
            seen_docs.add(c.doc_id)
            unique_citations.append(c)
            
    final_citations = unique_citations

    await write_audit_log(
        db, user_id=user_id, action="QUERY", outcome="ALLOW",
        resource_ids=sorted({c["doc_id"] for c in authorized})[:50],
        client_ip=client_ip, roles=roles
    )
    
    db.add(ChatMessage(session_id=session_id, role="user", content=q))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=answer, citations=orjson.dumps([c.model_dump() for c in final_citations]).decode()))
    
    await db.commit()

    return QueryResponse(
        answer=answer,
        citations=final_citations,
        debug=QueryDebug(retrieved_total=retrieved_total, authorized_total=len(authorized)),
        session_id=session_id
    )
