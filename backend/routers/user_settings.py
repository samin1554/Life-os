"""User settings routes — API key management."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from openai import AsyncOpenAI

from core.database import get_db
from core.security import get_current_user
from core.encryption import encrypt_value, decrypt_value
from models import User, UserApiKey

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

# Known providers and their base URLs
PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": None,  # Anthropic uses its own SDK, not OpenAI-compatible
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "perplexity": "https://api.perplexity.ai",
    "tavily": None,  # Not an LLM provider
}

PROVIDER_TEST_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "openrouter": "openrouter/free",
    "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "fireworks": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "mistral": "mistral-small-latest",
    "deepseek": "deepseek-chat",
    "perplexity": "llama-3.1-sonar-small-128k-online",
}


# ── Schemas ──────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    provider: str
    api_key: str
    label: str = "default"
    base_url: Optional[str] = None
    is_primary: bool = False


class ApiKeyUpdate(BaseModel):
    api_key: Optional[str] = None
    label: Optional[str] = None
    base_url: Optional[str] = None
    is_primary: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    label: str
    key_suffix: str
    base_url: Optional[str]
    is_primary: bool
    created_at: str

    class Config:
        from_attributes = True


# ── Endpoints ────────────────────────────────────────────

@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user (masked — never returns full key)."""
    result = await db.execute(
        select(UserApiKey)
        .where(UserApiKey.user_id == current_user.id)
        .order_by(UserApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return {
        "api_keys": [
            {
                "id": str(k.id),
                "provider": k.provider,
                "label": k.label,
                "key_suffix": k.key_suffix,
                "base_url": k.base_url,
                "is_primary": k.is_primary,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]
    }


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def add_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new API key for a provider."""
    if len(body.api_key) < 4:
        raise HTTPException(status_code=400, detail="API key too short")

    # If setting as primary, unset any existing primary for this user
    if body.is_primary:
        await db.execute(
            update(UserApiKey)
            .where(UserApiKey.user_id == current_user.id, UserApiKey.is_primary == True)
            .values(is_primary=False)
        )

    key = UserApiKey(
        user_id=current_user.id,
        provider=body.provider,
        label=body.label,
        base_url=body.base_url or PROVIDER_BASE_URLS.get(body.provider),
        encrypted_key=encrypt_value(body.api_key),
        key_suffix=body.api_key[-4:],
        is_primary=body.is_primary,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    return {
        "id": str(key.id),
        "provider": key.provider,
        "label": key.label,
        "key_suffix": key.key_suffix,
        "is_primary": key.is_primary,
    }


@router.put("/api-keys/{key_id}")
async def update_api_key(
    key_id: UUID,
    body: ApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing API key."""
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.id == key_id, UserApiKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    if body.api_key is not None:
        if len(body.api_key) < 4:
            raise HTTPException(status_code=400, detail="API key too short")
        key.encrypted_key = encrypt_value(body.api_key)
        key.key_suffix = body.api_key[-4:]

    if body.label is not None:
        key.label = body.label
    if body.base_url is not None:
        key.base_url = body.base_url

    if body.is_primary is True:
        # Unset other primaries first
        await db.execute(
            update(UserApiKey)
            .where(
                UserApiKey.user_id == current_user.id,
                UserApiKey.is_primary == True,
                UserApiKey.id != key_id,
            )
            .values(is_primary=False)
        )
        key.is_primary = True
    elif body.is_primary is False:
        key.is_primary = False

    await db.commit()
    return {"status": "updated"}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an API key."""
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.id == key_id, UserApiKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(key)
    await db.commit()
    return {"status": "deleted"}


@router.post("/api-keys/{key_id}/verify")
async def verify_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify an API key by making a lightweight test call."""
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.id == key_id, UserApiKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    try:
        decrypted = decrypt_value(key.encrypted_key)
    except ValueError:
        raise HTTPException(status_code=500, detail="Failed to decrypt key")

    # For Tavily, just check the key format
    if key.provider == "tavily":
        return {"status": "ok", "message": "Tavily key stored (format check only)"}

    # For LLM providers, try a minimal completion
    test_model = PROVIDER_TEST_MODELS.get(key.provider, "gpt-4o-mini")
    base_url = key.base_url

    if not base_url:
        return {"status": "warning", "message": "No base URL configured — cannot verify"}

    try:
        client = AsyncOpenAI(api_key=decrypted, base_url=base_url)
        response = await client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=5,
        )
        return {"status": "ok", "message": f"Key verified with {key.provider}"}
    except Exception as e:
        logger.warning("API key verification failed for %s: %s", key.provider, e)
        raise HTTPException(status_code=400, detail=f"Key verification failed: {str(e)}")


@router.patch("/dismiss-api-key-disclaimer")
async def dismiss_api_key_disclaimer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently dismiss the API key disclaimer for this user."""
    current_user.api_key_disclaimer_dismissed = True
    await db.commit()
    return {"status": "dismissed"}
