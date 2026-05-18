"""Groq LLM client for Life OS agents (OpenAI-compatible API)."""
from typing import Optional
from uuid import UUID
import json
import logging

from openai import AsyncOpenAI, APIError, RateLimitError, AuthenticationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_CHAT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_EXTRACT_MODEL = "llama-3.1-8b-instant"
OPENROUTER_FALLBACK_MODEL = "openrouter/free"

_groq_client: Optional[AsyncOpenAI] = None
_openrouter_client: Optional[AsyncOpenAI] = None


def get_llm_client() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
        )
    return _groq_client


def get_openrouter_client() -> Optional[AsyncOpenAI]:
    global _openrouter_client
    if _openrouter_client is None and settings.openrouter_api_key:
        _openrouter_client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
        )
    return _openrouter_client


async def get_user_llm_client(
    user_id: "str | UUID", db: AsyncSession
) -> Optional[tuple[AsyncOpenAI, str]]:
    """Get a user's primary LLM client if they have configured their own API key.

    Returns:
        Tuple of (AsyncOpenAI client, model_name) if user has a key configured,
        or None to fall back to system defaults.
    """
    from models import UserApiKey
    from core.encryption import decrypt_value

    # Normalize user_id to UUID for DB query
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # Look for user's primary LLM key first, then any LLM key
    result = await db.execute(
        select(UserApiKey)
        .where(
            UserApiKey.user_id == user_id,
            UserApiKey.provider.notin_(["tavily"]),  # Exclude non-LLM providers
        )
        .order_by(UserApiKey.is_primary.desc(), UserApiKey.created_at.desc())
    )
    key = result.scalars().first()

    if not key:
        logger.warning("No API key found for user %s (checked user_api_keys table)", user_id)
        return None

    logger.info("Found API key for user %s: provider=%s, base_url=%s, suffix=%s", user_id, key.provider, key.base_url, key.key_suffix)

    try:
        decrypted = decrypt_value(key.encrypted_key)
    except ValueError:
        logger.error("Failed to decrypt user API key %s for user %s", key.id, user_id)
        return None

    if not key.base_url:
        logger.warning("User key %s has no base_url, cannot create client", key.id)
        return None

    # Determine default model for provider
    provider_models = {
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-sonnet-4-20250514",
        "openrouter": "openrouter/free",
        "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "fireworks": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "mistral": "mistral-small-latest",
        "deepseek": "deepseek-chat",
        "perplexity": "llama-3.1-sonar-small-128k-online",
    }
    model = provider_models.get(key.provider, "gpt-4o-mini")

    client = AsyncOpenAI(api_key=decrypted, base_url=key.base_url)
    return (client, model)


def _build_messages(system_prompt: str, messages: list[dict]) -> list[dict]:
    """Prepend system prompt to messages for OpenAI-compatible format."""
    return [{"role": "system", "content": system_prompt}, *messages]


async def _try_provider_chat(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, messages),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if not response.choices:
            logger.warning("%s returned no choices", model)
            return None
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning("%s chat failed: %s", model, e)
        return None


async def _try_provider_extract(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> Optional[dict]:
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, messages),
            max_tokens=max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw": text}
    except Exception as e:
        logger.warning("%s extraction failed: %s", model, e)
        return None


async def _fallback_chat(
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    """Try OpenRouter as fallback."""
    openrouter = get_openrouter_client()
    if openrouter:
        result = await _try_provider_chat(
            openrouter, OPENROUTER_FALLBACK_MODEL, system_prompt, messages, temperature, max_tokens
        )
        if result is not None:
            return result

    return None


async def _fallback_extract(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> Optional[dict]:
    """Try OpenRouter as fallback for structured extraction."""
    openrouter = get_openrouter_client()
    if openrouter:
        result = await _try_provider_extract(
            openrouter, OPENROUTER_FALLBACK_MODEL, system_prompt, messages, max_tokens
        )
        if result is not None:
            return result

    return None


async def chat_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    user_id: "Optional[str | UUID]" = None,
    db: Optional[AsyncSession] = None,
) -> str:
    """Send a chat completion request, using user's key if available, with cascading fallback."""
    NO_KEY_MSG = "Please add your API key in Settings to use AI features. Free keys are available from providers like Groq."

    # Try user's own API key first
    if user_id and db:
        logger.info("chat_completion: looking up key for user_id=%s (type=%s)", user_id, type(user_id).__name__)
        user_client_info = await get_user_llm_client(user_id, db)
        if user_client_info:
            user_client, user_model = user_client_info
            result = await _try_provider_chat(
                user_client, user_model, system_prompt, messages, temperature, max_tokens
            )
            if result is not None:
                logger.info("Using user's own API key for chat completion (provider key)")
                return result
            logger.warning("User's API key failed, falling back to system key")
        else:
            logger.warning("chat_completion: no user key found, user_id=%s", user_id)

    # In production, require user keys — don't fall back to system keys
    if settings.environment == "production":
        logger.warning("Production mode: returning NO_KEY_MSG for user_id=%s", user_id)
        return NO_KEY_MSG

    client = get_llm_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, messages),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except RateLimitError as e:
        logger.warning("Groq rate limit exceeded for %s, trying fallback providers: %s", model, e)
        fallback = await _fallback_chat(system_prompt, messages, temperature, max_tokens)
        if fallback is not None:
            logger.info("Using fallback provider for chat completion")
            return fallback
        return "I'm temporarily at capacity due to high demand. Please try again in a few minutes."
    except AuthenticationError as e:
        logger.error("Groq authentication failed: %s", e)
        return "There's an issue with the AI service configuration. Please contact support."
    except APIError as e:
        logger.error("Groq API error: %s", e)
        return "The AI service encountered an error. Please try again shortly."
    except Exception as e:
        logger.error("Unexpected LLM error: %s", e)
        return "Something went wrong while processing your request. Please try again."


async def chat_completion_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    user_id: "Optional[str | UUID]" = None,
    db: Optional[AsyncSession] = None,
) -> dict:
    """Chat completion with native function calling (tools API).

    Returns:
        {
            "content": str | None,       # Text content (if any)
            "tool_calls": list[dict],     # [{name, arguments}] (if any)
            "raw_message": message obj,   # Full message object for conversation threading
        }
    """
    # Try user's own API key first
    if user_id and db:
        user_client_info = await get_user_llm_client(user_id, db)
        if user_client_info:
            user_client, user_model = user_client_info
            try:
                response = await user_client.chat.completions.create(
                    model=user_model,
                    messages=_build_messages(system_prompt, messages),
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                msg = response.choices[0].message
                tool_calls = []
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                        tool_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": args,
                        })
                logger.info("Using user's own API key for tool calling")
                return {
                    "content": msg.content,
                    "tool_calls": tool_calls,
                    "raw_message": None,
                }
            except Exception as e:
                logger.warning("User's API key failed for tool calling, falling back: %s", e)

    # In production, require user keys — don't fall back to system keys
    if settings.environment == "production":
        return {
            "content": "Please add your API key in Settings to use AI features. Free keys are available from providers like Groq.",
            "tool_calls": [],
            "raw_message": None,
        }

    client = get_llm_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, messages),
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "raw_message": None,
        }
    except RateLimitError as e:
        logger.warning("Groq rate limit in tool calling for %s: %s", model, e)
        # Try fallbacks with tools support
        fallback = await _fallback_chat_with_tools(
            system_prompt, messages, tools, temperature, max_tokens
        )
        if fallback is not None:
            return fallback
        return {"content": "Rate limited. Please try again shortly.", "tool_calls": [], "raw_message": None}
    except APIError as e:
        # On 400 errors (malformed tool calls), retry without native tools
        # and let the text-based parser in tool_runner handle it
        if e.status_code == 400 and "tool" in str(e).lower():
            logger.warning("Tool calling 400 error, retrying without native tools: %s", e)
            try:
                from core.tools import format_tools_for_prompt
                # Build a text-based tool prompt so the model can still use tools
                # We need the Tool objects, but we only have the API format here.
                # Return empty content so tool_runner can retry on next iteration.
                response = await client.chat.completions.create(
                    model=model,
                    messages=_build_messages(system_prompt, messages),
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                msg = response.choices[0].message
                return {
                    "content": msg.content,
                    "tool_calls": [],
                    "raw_message": None,
                }
            except Exception as retry_e:
                logger.error("Retry without tools also failed: %s", retry_e)
        logger.error("Tool calling error: %s", e)
        return {"content": f"Error: {e}", "tool_calls": [], "raw_message": None}
    except Exception as e:
        logger.error("Tool calling error: %s", e)
        return {"content": f"Error: {e}", "tool_calls": [], "raw_message": None}


async def _fallback_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> Optional[dict]:
    """Try OpenRouter with native tool calling."""
    for get_client, model_name in [
        (get_openrouter_client, OPENROUTER_FALLBACK_MODEL),
    ]:
        client = get_client()
        if not client:
            continue
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=_build_messages(system_prompt, messages),
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            msg = response.choices[0].message
            tool_calls = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args,
                    })
            logger.info("Fallback tool calling succeeded with %s", model_name)
            return {
                "content": msg.content,
                "tool_calls": tool_calls,
                "raw_message": None,
            }
        except Exception as e:
            logger.warning("Fallback %s tool calling failed: %s", model_name, e)
            continue
    return None


async def extract_structured(
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_EXTRACT_MODEL,
    max_tokens: int = 1024,
    user_id: "Optional[str | UUID]" = None,
    db: Optional[AsyncSession] = None,
) -> dict:
    """Extract structured JSON from the LLM, with cascading fallback on rate limits."""
    NO_KEY_MSG = "Please add your API key in Settings to use AI features. Free keys are available from providers like Groq."

    # Try user's own API key first
    if user_id and db:
        user_client_info = await get_user_llm_client(user_id, db)
        if user_client_info:
            user_client, user_model = user_client_info

            # Try with response_format first, fall back without it
            for use_json_format in [True, False]:
                try:
                    kwargs = {
                        "model": user_model,
                        "messages": _build_messages(system_prompt, messages),
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    }
                    if use_json_format:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = await user_client.chat.completions.create(**kwargs)
                    text = response.choices[0].message.content or "{}"
                    try:
                        if "```json" in text:
                            text = text.split("```json")[1].split("```")[0].strip()
                        elif "```" in text:
                            text = text.split("```")[1].split("```")[0].strip()
                        return json.loads(text)
                    except (json.JSONDecodeError, IndexError):
                        return {"raw": text}
                except Exception as e:
                    if use_json_format and "response_format" in str(e).lower():
                        logger.info("Provider doesn't support response_format, retrying without it")
                        continue
                    logger.warning("User key failed for extract_structured: %s", e)
                    break

    # In production, require user keys
    if settings.environment == "production":
        return {"error": "no_api_key", "message": NO_KEY_MSG}

    client = get_llm_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, messages),
            max_tokens=max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw": text}
    except RateLimitError as e:
        logger.warning("Groq rate limit exceeded in extract_structured, trying fallbacks: %s", e)
        fallback = await _fallback_extract(system_prompt, messages, max_tokens)
        if fallback is not None:
            return fallback
        return {"error": "rate_limited", "message": "AI service rate limit reached. Try again shortly."}
    except APIError as e:
        logger.error("Groq API error in extract_structured: %s", e)
        return {"error": "api_error", "message": str(e)}
    except Exception as e:
        logger.error("Unexpected LLM error in extract_structured: %s", e)
        return {"error": "unexpected", "message": str(e)}
