from fastapi import APIRouter, Depends, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE
from app.api.deps import get_current_user, get_client_ip
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.db.models import Document, DocumentChunk
from app.schemas.documents import UploadResponse, DocumentWithChunks, DocumentOut, ChunkOut
from app.services.doc_ingest import ingest_document
from app.services.audit_log import write_audit_log
from app.services.neo4j_rbac import RBACGraph

router = APIRouter(prefix="/documents")

@router.post("/upload", response_model=UploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...), title: str = "Untitled",
                          db: AsyncSession = Depends(get_db), user=Depends(get_current_user),
                          client_ip: str = Depends(get_client_ip)) -> UploadResponse:
    user_id = user["user_id"]; roles=user.get("roles", [])
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise AppError("File too large", status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, code="UPLOAD_TOO_LARGE")
    storage_dir = Path(settings.doc_storage_dir); storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload.txt").name
    path = storage_dir / safe_name
    path.write_bytes(data)
    
    if safe_name.lower().endswith('.pdf'):
        import io
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            content_text = "\n\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except Exception:
            raise AppError("Failed to parse PDF file", status_code=400, code="INVALID_PDF")
    else:
        content_text = data.decode("utf-8", errors="replace").replace('\x00', '')
        
    doc_id, chunks_created = await ingest_document(db, title=title, filename=safe_name, storage_path=str(path), content_text=content_text)
    await write_audit_log(db, user_id=user_id, action="DOCUMENT_UPLOAD", outcome="ALLOW", resource_ids=[doc_id], client_ip=client_ip, roles=roles)
    await db.commit()
    
    rbac = RBACGraph()
    await rbac.add_document(doc_id=doc_id)
    await rbac.add_policy("admin", doc_id=doc_id, permission="READ")
    
    return UploadResponse(doc_id=doc_id, chunks_created=chunks_created)

@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if "admin" not in user.get("roles", []):
        raise AppError("Admin role required", status_code=403, code="FORBIDDEN")
    docs = (await db.execute(select(Document).order_by(Document.created_at.desc()))).scalars().all()
    return [DocumentOut(id=d.id, title=d.title, filename=d.filename, created_at=d.created_at) for d in docs]

@router.get("/{doc_id}", response_model=DocumentWithChunks)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if "admin" not in user.get("roles", []):
        raise AppError("Admin role required", status_code=403, code="FORBIDDEN")
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if not doc:
        raise AppError("Document not found", status_code=404, code="NOT_FOUND")
    res = await db.execute(select(DocumentChunk).where(DocumentChunk.doc_id==doc_id).order_by(DocumentChunk.chunk_index.asc()))
    chunks = res.scalars().all()
    return DocumentWithChunks(
        document=DocumentOut(id=doc.id, title=doc.title, filename=doc.filename, created_at=doc.created_at),
        chunks=[ChunkOut(id=c.id, chunk_index=c.chunk_index, content=c.content) for c in chunks],
    )

from fastapi.responses import FileResponse

@router.get("/{doc_id}/download")
async def download_document(doc_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), client_ip: str = Depends(get_client_ip)):
    user_id = user["user_id"]; roles=user.get("roles", [])
    
    # 1. Authorize via Neo4j Graph
    allowed_docs = set(await RBACGraph().allowed_doc_ids(user_id=user_id, roles=roles))
    if doc_id not in allowed_docs:
        await write_audit_log(db, user_id=user_id, action="DOCUMENT_DOWNLOAD", outcome="DENY", resource_ids=[doc_id], client_ip=client_ip, roles=roles)
        await db.commit()
        raise AppError("Insufficient access to download document", status_code=403, code="FORBIDDEN")
        
    # 2. Get document metadata from Postgres
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if not doc:
        raise AppError("Document not found", status_code=404, code="NOT_FOUND")
        
    # 3. Log and serve file
    await write_audit_log(db, user_id=user_id, action="DOCUMENT_DOWNLOAD", outcome="ALLOW", resource_ids=[doc_id], client_ip=client_ip, roles=roles)
    await db.commit()
    
    return FileResponse(path=doc.storage_path, filename=doc.filename)

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), client_ip: str = Depends(get_client_ip)):
    user_id = user["user_id"]; roles=user.get("roles", [])
    if "admin" not in roles:
        raise AppError("Admin role required to delete documents", status_code=403, code="FORBIDDEN")
        
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if not doc:
        raise AppError("Document not found", status_code=404, code="NOT_FOUND")
        
    # 1. Delete from ChromaDB
    from app.services.chroma_client import ChromaHttpClient
    try:
        await ChromaHttpClient().delete(where={"doc_id": doc_id})
    except Exception as e:
        print(f"Warning: Failed to delete from ChromaDB: {e}")
        
    # 2. Delete from Filesystem
    try:
        Path(doc.storage_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Failed to delete file: {e}")
        
    # 3. Delete from Neo4j
    await RBACGraph().remove_document(doc_id=doc_id)
        
    # 4. Delete from Postgres (Cascade will handle chunks)
    await db.delete(doc)
    
    # 5. Audit Log
    await write_audit_log(db, user_id=user_id, action="DOCUMENT_DELETE", outcome="ALLOW", resource_ids=[doc_id], client_ip=client_ip, roles=roles)
    await db.commit()
    
    return {"message": "Document deleted successfully"}
