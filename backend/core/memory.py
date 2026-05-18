"""Memory layer helpers for semantic memory (Chroma-based)."""
import uuid
from typing import List, Optional
from datetime import datetime, timezone

import chromadb

from core.config import get_settings

settings = get_settings()

_chroma_client: Optional[chromadb.HttpClient] = None


def get_chroma_client() -> chromadb.HttpClient:
    global _chroma_client
    if _chroma_client is None:
        import logging
        logger = logging.getLogger(__name__)
        host = settings.chroma_host
        port = settings.chroma_port
        auth_token = settings.chroma_auth_token

        logger.info("Connecting to ChromaDB at %s:%s (auth=%s)", host, port, bool(auth_token))

        kwargs = {"host": host, "port": port}

        # Support Railway auth proxy token
        if auth_token:
            kwargs["headers"] = {
                "Authorization": f"Bearer {auth_token}",
                "X-Api-Key": auth_token,
            }

        _chroma_client = chromadb.HttpClient(**kwargs)

        # Test connectivity
        try:
            _chroma_client.heartbeat()
            logger.info("ChromaDB heartbeat OK")
        except Exception as e:
            logger.error("ChromaDB heartbeat FAILED: %s", e)
            _chroma_client = None
            raise

    return _chroma_client


def _get_collection():
    global _chroma_client
    try:
        client = get_chroma_client()
        return client.get_or_create_collection(name="lifeos_memories")
    except Exception:
        # Reset client so next call retries connection
        _chroma_client = None
        raise


def save_memory(
    user_id: str,
    content: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Save a memory for a user. Returns the stored memory record."""
    collection = _get_collection()
    memory_id = str(uuid.uuid4())
    
    meta = metadata or {}
    meta["user_id"] = user_id
    meta["content"] = content
    meta["created_at"] = datetime.now(timezone.utc).isoformat()
    
    collection.add(
        ids=[memory_id],
        documents=[content],
        metadatas=[meta],
    )
    
    return {
        "id": memory_id,
        "user_id": user_id,
        "content": content,
        "metadata": meta,
    }


def retrieve_memories(
    user_id: str,
    query: str,
    limit: int = 10,
    filters: Optional[dict] = None,
) -> List[dict]:
    """Retrieve relevant memories for a user and query."""
    collection = _get_collection()
    
    where_clause = {"user_id": user_id}
    if filters:
        where_clause.update(filters)
    
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where=where_clause,
    )
    
    memories = []
    if results["ids"] and results["ids"][0]:
        for i, memory_id in enumerate(results["ids"][0]):
            memories.append({
                "id": memory_id,
                "content": results["documents"][0][i] if results["documents"] else None,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
    
    return memories


def delete_all_memories(user_id: str) -> None:
    """Delete all memories for a user."""
    collection = _get_collection()
    collection.delete(where={"user_id": user_id})
