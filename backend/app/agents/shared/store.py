"""
Chroma + Bedrock embeddings. Used by jobs agent and chat.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

DEFAULT_COLLECTION = "jobs_and_resumes"
BEDROCK_EMBED_MODEL = "amazon.titan-embed-text-v2:0"


def _bedrock_embed(texts: list[str]) -> list[list[float]]:
    import boto3
    region = settings.aws_region or "us-east-1"
    client = boto3.client("bedrock-runtime", region_name=region)
    embeddings = []
    for text in texts:
        body = json.dumps({"inputText": text[:8192]})
        response = client.invoke_model(
            modelId=BEDROCK_EMBED_MODEL,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        out = json.loads(response["body"].read())
        embeddings.append(out["embedding"])
    return embeddings


def _get_chroma_client(persist_path: str | Path | None = None):
    if settings.chroma_host:
        return chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    path = Path(persist_path or settings.chroma_data_path)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_store(
    persist_path: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION,
) -> "VectorStore":
    client = _get_chroma_client(persist_path)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Jobs and resumes"},
    )
    return VectorStore(collection=collection)


class VectorStore:
    def __init__(self, collection: chromadb.Collection):
        self._collection = collection

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        if not texts:
            return []
        if metadatas is None:
            metadatas = [{}] * len(texts)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        if len(metadatas) != len(texts):
            metadatas = [metadatas[0] if metadatas else {}] * len(texts)
        if len(ids) != len(texts):
            ids = [str(uuid.uuid4()) for _ in texts]
        safe_metadatas = []
        for m in metadatas:
            safe = {k: v for k, v in m.items() if isinstance(v, (str, int, float, bool))}
            safe_metadatas.append(safe)
        embeddings = _bedrock_embed(texts)
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=safe_metadatas)
        return ids

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        if top_k <= 0:
            return []
        [query_embed] = _bedrock_embed([query])
        result = self._collection.query(
            query_embeddings=[query_embed],
            n_results=top_k,
            include=["documents"],
        )
        docs = result.get("documents") or []
        return docs[0] if docs else []

    def retrieve_with_metadata(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return list of {document, url, title, chroma_id} for chat citations."""
        if top_k <= 0:
            return []
        [query_embed] = _bedrock_embed([query])
        result = self._collection.query(
            query_embeddings=[query_embed],
            n_results=top_k,
            include=["documents", "metadatas"],
        )
        docs = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        # Chroma returns ids in result by default; valid include values are documents, metadatas, etc. (not "ids")
        ids = (result.get("ids") or [[]])[0]
        out = []
        for i, doc in enumerate(docs):
            meta = (metadatas[i] or {}) if i < len(metadatas) else {}
            out.append({
                "document": doc or "",
                "url": meta.get("url") or "",
                "title": meta.get("title") or "",
                "chroma_id": ids[i] if i < len(ids) else "",
            })
        return out


def clear_collection(
    persist_path: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION,
) -> int:
    client = _get_chroma_client(persist_path)
    try:
        coll = client.get_collection(name=collection_name)
    except Exception:
        return 0
    result = coll.get(include=[])
    ids = result.get("ids") or []
    if ids:
        coll.delete(ids=ids)
    return len(ids)
