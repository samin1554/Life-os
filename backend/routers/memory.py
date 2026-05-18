"""Memory/privacy routes — view and delete stored memories."""
import logging
from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user
from core.memory import retrieve_memories, save_memory, delete_all_memories, _get_collection
from models import User
from schemas.memory import MemoryResponse, MemoryListResponse, MemoryDeleteResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    current_user: User = Depends(get_current_user),
):
    """View all stored memories for the current user."""
    user_id = str(current_user.id)
    try:
        collection = _get_collection()

        results = collection.get(
            where={"user_id": user_id},
            limit=100,
        )

        memories = []
        if results["ids"]:
            for i, memory_id in enumerate(results["ids"]):
                memories.append(MemoryResponse(
                    id=memory_id,
                    content=results["documents"][i] if results["documents"] else None,
                    metadata=results["metadatas"][i] if results["metadatas"] else None,
                ))

        return {"memories": memories, "total": len(memories)}
    except Exception as e:
        logger.error("ChromaDB connection failed: %s", e)
        return {"memories": [], "total": 0}


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a specific memory by ID."""
    user_id = str(current_user.id)
    collection = _get_collection()

    existing = collection.get(ids=[memory_id])
    if not existing["ids"]:
        return {"deleted": False}

    if existing["metadatas"] and existing["metadatas"][0].get("user_id") != user_id:
        return {"deleted": False}

    collection.delete(ids=[memory_id])
    return {"deleted": True}


@router.delete("", response_model=MemoryDeleteResponse)
async def delete_all_user_memories(
    current_user: User = Depends(get_current_user),
):
    """Delete all memories for the current user."""
    user_id = str(current_user.id)

    collection = _get_collection()
    existing = collection.get(where={"user_id": user_id})
    count = len(existing["ids"]) if existing["ids"] else 0

    if count > 0:
        delete_all_memories(user_id)

    return {"deleted": True, "count": count}
