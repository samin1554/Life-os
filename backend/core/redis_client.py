"""Redis client for session state, caching, and agent event pub/sub."""
from typing import Optional, AsyncIterator
import json

import redis
import redis.asyncio as aioredis

from core.config import get_settings

settings = get_settings()

_redis_client: Optional[redis.Redis] = None
_async_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_async_redis() -> aioredis.Redis:
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
    return _async_redis_client


def _agent_channel(user_id: str) -> str:
    return f"agent_events:{user_id}"


async def publish_agent_event(user_id: str, event: dict) -> None:
    r = await get_async_redis()
    await r.publish(_agent_channel(user_id), json.dumps(event))


async def subscribe_agent_events(user_id: str) -> AsyncIterator[dict]:
    r = await get_async_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_agent_channel(user_id))
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(_agent_channel(user_id))
        await pubsub.aclose()


def get_onboarding_state(user_id: str) -> dict:
    """Get onboarding state from Redis. Returns default if not found."""
    r = get_redis_client()
    key = f"onboarding:{user_id}"
    data = r.get(key)
    if data:
        return json.loads(data)
    return {
        "step": 0,
        "total_steps": 10,
        "answers": [],
        "complete": False,
        "session_id": None,
    }


def set_onboarding_state(user_id: str, state: dict, ttl: int = 3600) -> None:
    """Save onboarding state to Redis with TTL (default 1 hour)."""
    r = get_redis_client()
    key = f"onboarding:{user_id}"
    r.setex(key, ttl, json.dumps(state))


def delete_onboarding_state(user_id: str) -> None:
    r = get_redis_client()
    key = f"onboarding:{user_id}"
    r.delete(key)
