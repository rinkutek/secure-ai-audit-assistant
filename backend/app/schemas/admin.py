from pydantic import BaseModel, EmailStr, Field
from typing import List

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    roles: List[str] = []

class UserOut(BaseModel):
    id: str
    email: EmailStr
    roles: List[str]
    is_active: bool

class UserUpdateRoles(BaseModel):
    roles: List[str]

class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64)

class RoleOut(BaseModel):
    id: str
    name: str

class PolicyCreate(BaseModel):
    role_name: str = Field(min_length=2, max_length=64)
    doc_id: str
    permission: str = Field(default="READ", pattern="^(READ|WRITE)$")

class PolicyOut(BaseModel):
    id: str
    role_name: str
    doc_id: str
    permission: str

class GraphNode(BaseModel):
    id: str
    label: str
    type: str

class GraphEdge(BaseModel):
    source: str
    target: str
    label: str

class GraphData(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphEdge]
