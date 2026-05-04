from __future__ import annotations

from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings as ChromaSettings
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.core.config import settings
from app.core.exceptions import AppError


class ChromaHttpClient:
    """
    Uses the official chromadb Python client in HTTP mode.
    This avoids having to track low-level REST payload shapes that can vary by version.
    """

    def __init__(self) -> None:
        # CHROMA_HTTP_URL like: http://chromadb:8000
        url = settings.chroma_http_url.rstrip("/")
        # Parse host/port from URL (simple + safe for our env)
        # url will be http://host:port
        try:
            scheme, rest = url.split("://", 1)
            if ":" in rest:
                host, port_s = rest.split(":", 1)
                port = int(port_s)
            else:
                host = rest
                port = 80 if scheme == "http" else 443
        except Exception as e:
            raise AppError(
                f"Invalid CHROMA_HTTP_URL: {settings.chroma_http_url}",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                code="CHROMA_CONFIG_ERROR",
            ) from e

        self._client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=(scheme == "https"),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )
        self.collection_name = settings.chroma_collection

    def _get_or_create_collection(self):
        try:
            return self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise AppError(
                "Vector store unavailable",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                code="CHROMA_UNAVAILABLE",
            ) from e

    async def upsert(
        self,
        *,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        documents: List[str],
    ) -> None:
        try:
            col = self._get_or_create_collection()
            col.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
        except Exception as e:
            raise AppError(
                "Vector store unavailable",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                code="CHROMA_UNAVAILABLE",
            ) from e

    async def query(self, *, query_embeddings: List[List[float]], n_results: int) -> List[Dict[str, Any]]:
        try:
            col = self._get_or_create_collection()
            res = col.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                include=["metadatas", "documents", "distances"],
            )

            out: List[Dict[str, Any]] = []
            ids = res.get("ids", [[]])[0]
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            for i in range(len(ids)):
                out.append(
                    {
                        "id": ids[i],
                        "document": docs[i],
                        "metadata": metas[i] or {},
                        "distance": dists[i],
                    }
                )
            return out
        except Exception as e:
            raise AppError(
                "Vector store unavailable",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                code="CHROMA_UNAVAILABLE",
            ) from e