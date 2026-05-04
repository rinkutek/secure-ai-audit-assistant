from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="Secure AI Audit Assistant", alias="APP_NAME")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    jwt_issuer: str = Field(default="secure-ai-audit-assistant", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="secure-ai-audit", alias="JWT_AUDIENCE")
    jwt_access_ttl_seconds: int = Field(default=900, alias="JWT_ACCESS_TTL_SECONDS")
    jwt_refresh_ttl_seconds: int = Field(default=604800, alias="JWT_REFRESH_TTL_SECONDS")
    jwt_signing_key: str = Field(default="change-me", alias="JWT_SIGNING_KEY")
    password_bcrypt_rounds: int = Field(default=12, alias="PASSWORD_BCRYPT_ROUNDS")

    database_url: str = Field(default="postgresql+asyncpg://secure:secure@postgres:5432/secure_audit", alias="DATABASE_URL")

    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="neo4jpassword", alias="NEO4J_PASSWORD")
    rbac_cache_ttl_seconds: int = Field(default=30, alias="RBAC_CACHE_TTL_SECONDS")

    chroma_http_url: str = Field(default="http://chromadb:8000", alias="CHROMA_HTTP_URL")
    chroma_collection: str = Field(default="doc_chunks", alias="CHROMA_COLLECTION")
    embedding_dim: int = Field(default=384, alias="EMBEDDING_DIM")

    rag_top_k: int = Field(default=8, alias="RAG_TOP_K")
    rag_keyword_top_k: int = Field(default=12, alias="RAG_KEYWORD_TOP_K")
    hybrid_alpha: float = Field(default=0.65, alias="HYBRID_ALPHA")

    mock_mode: bool = Field(default=True, alias="MOCK_MODE")
    mock_embeddings: bool = Field(default=True, alias="MOCK_EMBEDDINGS")
    openai_base_url: str = Field(default="http://localhost:11434/v1", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="local-dev", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    llm_request_timeout_seconds: int = Field(default=30, alias="LLM_REQUEST_TIMEOUT_SECONDS")

    # Azure OpenAI specific
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: str = Field(default="", alias="AZURE_OPENAI_KEY")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")

    doc_storage_dir: str = Field(default="/data/documents", alias="DOC_STORAGE_DIR")

    max_query_chars: int = Field(default=512, alias="MAX_QUERY_CHARS")
    max_upload_bytes: int = Field(default=5*1024*1024, alias="MAX_UPLOAD_BYTES")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("hybrid_alpha")
    @classmethod
    def _alpha(cls, v: float) -> float:
        if not (0 <= v <= 1):
            raise ValueError("HYBRID_ALPHA must be within [0,1]")
        return v

settings = Settings()
