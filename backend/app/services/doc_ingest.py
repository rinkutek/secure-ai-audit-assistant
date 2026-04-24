from typing import List, Tuple
from pathlib import Path
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Document, DocumentChunk, Embedding
from app.services.embeddings import get_embedding_provider
from app.services.chroma_client import ChromaHttpClient
from app.core.config import settings

_para = re.compile(r"\n\s*\n+")

def chunk_text(text: str, max_chars: int = 900) -> List[str]:
    paras=[p.strip() for p in _para.split(text) if p.strip()]
    chunks=[]; buf=""
    for p in paras:
        if len(buf)+len(p)+2 <= max_chars:
            buf=(buf+"\n\n"+p).strip()
        else:
            if buf: chunks.append(buf)
            buf=p
    if buf: chunks.append(buf)
    out=[]
    for c in chunks:
        if len(c)<=max_chars: out.append(c)
        else:
            for i in range(0,len(c),max_chars):
                out.append(c[i:i+max_chars])
    return out

async def ingest_document(session: AsyncSession, *, title: str, filename: str, storage_path: str, content_text: str) -> Tuple[str,int]:
    doc=Document(title=title, filename=filename, storage_path=storage_path)
    session.add(doc); await session.flush()
    texts=chunk_text(content_text)
    chunk_rows=[]
    for idx,t in enumerate(texts):
        ch=DocumentChunk(doc_id=doc.id, chunk_index=idx, content=t)
        session.add(ch); chunk_rows.append(ch)
    await session.flush()

    if not settings.mock_mode:
        embedder=get_embedding_provider()
        vectors=await embedder.embed([c.content for c in chunk_rows])
        chroma=ChromaHttpClient()
        await chroma.upsert(
            ids=[c.id for c in chunk_rows],
            embeddings=vectors,
            metadatas=[{"doc_id": c.doc_id, "chunk_id": c.id, "chunk_index": c.chunk_index} for c in chunk_rows],
            documents=[c.content for c in chunk_rows],
        )

    model = settings.openai_embedding_model if not settings.mock_mode else "mock-embeddings"
    for c in chunk_rows:
        session.add(Embedding(chunk_id=c.id, embedding_model=model))
    await session.flush()
    return doc.id, len(chunk_rows)
