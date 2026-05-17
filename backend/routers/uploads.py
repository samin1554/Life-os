"""File upload routes — user document management."""
import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from core.storage import get_storage
from models import User, UploadedFile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


def _extract_text_pdf(data: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pypdf not installed, skipping PDF extraction")
        return ""
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


def _extract_text_docx(data: bytes) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        logger.warning("python-docx not installed, skipping DOCX extraction")
        return ""
    except Exception as e:
        logger.warning("DOCX extraction failed: %s", e)
        return ""


def _extract_text(data: bytes, mime_type: str) -> str:
    """Extract text content based on MIME type."""
    if mime_type == "application/pdf":
        return _extract_text_pdf(data)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_text_docx(data)
    elif mime_type in ("text/plain", "text/markdown", "text/csv"):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")
    return ""


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = "general",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (max 10MB). Extracts text from PDFs, DOCX, and plain text."""
    # Validate MIME type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {content_type}. Allowed: PDF, DOCX, TXT, PNG, JPG",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Generate storage key with validated extension
    ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "txt", "md", "csv", "png", "jpg", "jpeg", "gif"}
    file_id = uuid.uuid4()
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "bin"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '.{ext}' not allowed")
    storage_key = f"uploads/{current_user.id}/{file_id}.{ext}"

    # Upload to storage
    storage = get_storage()
    stored_path = await storage.upload_from_bytes(data, storage_key)

    # Extract text
    extracted = _extract_text(data, content_type)

    # Save to DB
    upload_record = UploadedFile(
        id=file_id,
        user_id=current_user.id,
        filename=f"{file_id}.{ext}",
        original_name=file.filename or "unnamed",
        file_path=stored_path,
        mime_type=content_type,
        file_size_bytes=len(data),
        purpose=purpose,
        extracted_text=extracted if extracted else None,
    )
    db.add(upload_record)
    await db.commit()
    await db.refresh(upload_record)

    return {
        "id": str(upload_record.id),
        "original_name": upload_record.original_name,
        "mime_type": upload_record.mime_type,
        "file_size_bytes": upload_record.file_size_bytes,
        "purpose": upload_record.purpose,
        "has_extracted_text": bool(extracted),
        "created_at": upload_record.created_at.isoformat() if upload_record.created_at else None,
    }


@router.get("")
async def list_uploads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded files for the current user."""
    result = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.user_id == current_user.id)
        .order_by(UploadedFile.created_at.desc())
    )
    files = result.scalars().all()

    return {
        "files": [
            {
                "id": str(f.id),
                "original_name": f.original_name,
                "mime_type": f.mime_type,
                "file_size_bytes": f.file_size_bytes,
                "purpose": f.purpose,
                "has_extracted_text": bool(f.extracted_text),
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in files
        ]
    }


@router.get("/{file_id}/content")
async def get_upload_content(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the extracted text content of an uploaded file."""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.user_id == current_user.id,
        )
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": str(file.id),
        "original_name": file.original_name,
        "extracted_text": file.extracted_text or "",
    }


@router.delete("/{file_id}")
async def delete_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an uploaded file."""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.user_id == current_user.id,
        )
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete from storage
    storage = get_storage()
    try:
        await storage.delete(file.file_path)
    except Exception as e:
        logger.warning("Failed to delete file from storage: %s", e)

    await db.delete(file)
    await db.commit()
    return {"status": "deleted"}
