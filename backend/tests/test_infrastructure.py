"""Test all infrastructure components independently."""
import pytest
import redis
import chromadb
from sqlalchemy import text

from core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio(loop_scope="session")
async def test_postgres_connection(db_session):
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_redis_connection():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.set("lifeos:test", "hello")
    value = r.get("lifeos:test")
    r.delete("lifeos:test")
    assert value == "hello", f"Redis unexpected value: {value}"


def test_chroma_connection():
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    client.heartbeat()
    collection = client.get_or_create_collection(name="test_lifeos")
    collection.add(ids=["1"], documents=["test memory"])
    result = collection.query(query_texts=["test"], n_results=1)
    client.delete_collection(name="test_lifeos")
    assert result["ids"] and len(result["ids"][0]) > 0
