from typing import List
import hashlib, math
import httpx
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from app.core.config import settings
from app.core.exceptions import AppError

def _unit(v: List[float]) -> List[float]:
    n = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x/n for x in v]

class EmbeddingProvider:
    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class MockEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: List[str]) -> List[List[float]]:
        dim = settings.embedding_dim
        out=[]
        for t in texts:
            seed = hashlib.sha256(t.encode()).digest()
            vals=[]
            cur=seed
            while len(vals)<dim:
                cur = hashlib.sha256(cur).digest()
                for b in cur:
                    vals.append((b/255.0)*2-1)
                    if len(vals)>=dim: break
            out.append(_unit(vals))
        return out

class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: List[str]) -> List[List[float]]:
        url = settings.openai_base_url.rstrip('/') + '/embeddings'
        headers = {'Authorization': f'Bearer {settings.openai_api_key}'}
        body = {'model': settings.openai_embedding_model, 'input': texts}
        try:
            async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
                r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data=r.json()
            return [_unit(d['embedding']) for d in data['data']]
        except Exception:
            raise AppError("Embedding provider unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="EMBEDDINGS_UNAVAILABLE")

def get_embedding_provider() -> EmbeddingProvider:
    # Use mock embeddings if MOCK_EMBEDDINGS is true, or if we are in general MOCK_MODE
    if getattr(settings, 'mock_embeddings', False) or settings.mock_mode:
        return MockEmbeddingProvider()
    return OpenAICompatibleEmbeddingProvider()
