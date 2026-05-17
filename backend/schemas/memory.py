"""Memory Pydantic schemas."""
from typing import Optional

from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: str
    content: Optional[str] = None
    metadata: Optional[dict] = None
    distance: Optional[float] = None


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int


class MemoryDeleteResponse(BaseModel):
    deleted: bool
    count: Optional[int] = None
