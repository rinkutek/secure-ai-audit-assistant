from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    session_id: Optional[str] = None

class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    title: Optional[str] = None
    filename: Optional[str] = None
    chunk_index: Optional[int] = None

class QueryDebug(BaseModel):
    retrieved_total: int
    authorized_total: int

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    debug: QueryDebug
    session_id: str
