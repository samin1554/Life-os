"""File download endpoints for generated documents."""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from core.storage import get_storage
from models import User, GeneratedFile

router = APIRouter(prefix="/files", tags=["files"])

GENERATED_FILES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "generated_files"
)

MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".png": "image/png",
}


@router.get("")
async def list_files(
    format: Optional[str] = Query(None, pattern=r"^(docx|xlsx|pdf)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated files for the current user."""
    query = select(GeneratedFile).where(GeneratedFile.user_id == current_user.id)
    count_query = select(func.count()).select_from(GeneratedFile).where(
        GeneratedFile.user_id == current_user.id
    )

    if format:
        query = query.where(GeneratedFile.file_format == format)
        count_query = count_query.where(GeneratedFile.file_format == format)

    query = query.order_by(desc(GeneratedFile.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    files = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "files": [
            {
                "id": str(f.id),
                "filename": f.filename,
                "original_name": f.original_name,
                "file_format": f.file_format,
                "file_size_bytes": f.file_size_bytes,
                "template_used": f.template_used,
                "task_description": f.task_description,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in files
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{file_id}/download")
async def download_by_id(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file by its database ID."""
    result = await db.execute(
        select(GeneratedFile).where(
            GeneratedFile.id == file_id,
            GeneratedFile.user_id == current_user.id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage()
    if storage.is_s3:
        # Return presigned URL as JSON (avoids CORS issues with redirects)
        url = storage.get_download_url(file_record.file_path, filename=file_record.original_name)
        return {"download_url": url, "filename": file_record.original_name}
    else:
        # Local dev — serve file directly
        filepath = file_record.file_path
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404, detail="File no longer exists on disk"
            )
        ext = os.path.splitext(filepath)[1]
        return FileResponse(
            filepath,
            media_type=MIME_TYPES.get(ext, "application/octet-stream"),
            filename=file_record.original_name,
        )


@router.get("/download/{filename}")
async def download_by_filename(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file by its filename (legacy, also checks ownership via DB)."""
    result = await db.execute(
        select(GeneratedFile).where(
            GeneratedFile.filename == filename,
            GeneratedFile.user_id == current_user.id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage()
    if storage.is_s3:
        url = storage.get_download_url(file_record.file_path, filename=file_record.original_name)
        return {"download_url": url, "filename": file_record.original_name}
    else:
        filepath = file_record.file_path
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404, detail="File no longer exists on disk"
            )
        ext = os.path.splitext(filepath)[1]
        return FileResponse(
            filepath,
            media_type=MIME_TYPES.get(ext, "application/octet-stream"),
            filename=file_record.original_name,
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a generated file (DB record + disk file)."""
    result = await db.execute(
        select(GeneratedFile).where(
            GeneratedFile.id == file_id,
            GeneratedFile.user_id == current_user.id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete from storage (S3 or local disk)
    storage = get_storage()
    await storage.delete(file_record.file_path)

    # Delete from DB
    await db.delete(file_record)
    await db.commit()

    return {"deleted": True}
