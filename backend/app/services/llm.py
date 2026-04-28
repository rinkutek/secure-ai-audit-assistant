from typing import Any, Dict, List
import re
import httpx
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from app.core.config import settings
from app.core.exceptions import AppError

class LLMProvider:
    async def answer(self, *, question: str, context_chunks: List[Dict[str, Any]], past_messages: List[Dict[str, str]] = None) -> str:
        raise NotImplementedError

class MockLLMProvider(LLMProvider):
    async def answer(self, *, question: str, context_chunks: List[Dict[str, Any]], past_messages: List[Dict[str, str]] = None) -> str:
        q = question.lower()
        picks=[]
        for ch in context_chunks:
            for s in re.split(r"(?<=[.!?\n])\s+", ch['content']):
                if any(tok in s.lower() for tok in q.split()[:6]):
                    picks.append((s.strip(), ch['citation']))
        if not picks:
            for ch in context_chunks[:2]:
                s = re.split(r"(?<=[.!?\n])\s+", ch['content'].strip())[0].strip()
                if s: picks.append((s, ch['citation']))
        seen=set(); out=[]
        for s,c in picks:
            if s and s not in seen:
                seen.add(s); out.append(f"- {s} [{c}]")
            if len(out)>=5: break
        return "Grounded answer (mock mode):\n" + ("\n".join(out) if out else "I don't have enough authorized context to answer that.")

class OpenAICompatibleLLMProvider(LLMProvider):
    async def answer(self, *, question: str, context_chunks: List[Dict[str, Any]], past_messages: List[Dict[str, str]] = None) -> str:
        url = settings.openai_base_url.rstrip('/') + '/chat/completions'
        headers = {'Authorization': f'Bearer {settings.openai_api_key}'}
        context = "\n\n".join(f"[{ch['citation']}]\n{ch['content']}" for ch in context_chunks)
        
        system_prompt = (
            "You are a strict Secure AI Audit Assistant. "
            "You MUST answer the user's question relying ONLY on the provided context. "
            "If the provided context does not contain the information needed to answer the question, "
            "you MUST reply exactly with: 'I cannot answer this based on the provided authorized documents.' "
            "Do NOT use external knowledge and do NOT hallucinate. "
            "Always cite your sources using the format [DOC:<doc_id>#<chunk_index>] at the end of relevant sentences."
        )
        messages = [{"role":"system","content": system_prompt}]
        if past_messages:
            messages.extend(past_messages)
            
        user_content = (
            f"Context from Secure Vault:\n{context}\n\n"
            f"User Question: {question}\n\n"
            "CRITICAL INSTRUCTION: You MUST answer the user's question relying ONLY on the 'Context from Secure Vault' above. "
            "If the context does not contain the answer, you MUST reply exactly with: 'I cannot answer this based on the provided authorized documents.' "
            "Do NOT use external knowledge and do NOT hallucinate. "
            "You MUST cite your sources by appending the exact string [DOC:<doc_id>] at the end of every sentence you write."
        )
        messages.append({"role":"user","content": user_content})
        
        body = {
            "model": settings.openai_chat_model,
            "messages": messages,
            "temperature": 0.0
        }
        try:
            async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
                r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception:
            raise AppError("LLM provider unavailable", status_code=HTTP_503_SERVICE_UNAVAILABLE, code="LLM_UNAVAILABLE")

def get_llm_provider() -> LLMProvider:
    return MockLLMProvider() if settings.mock_mode else OpenAICompatibleLLMProvider()
