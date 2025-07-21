import os
import mimetypes
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
import logging
from ..core.database import get_db
from ..core.auth import get_current_active_user
from ..core.models import Master, Employee, Administrator
from ..core.config import settings
from ..utils.file_security import (
    validate_and_save_file,
    FileSecurityError,
    delete_file_safely,
)

router = APIRouter()

# Используем относительный путь от корня приложения
UPLOAD_DIR = os.path.join("media", "gorod", "rashod")

# Расширенная валидация файлов
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Опасные расширения и MIME-типы
DANGEROUS_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".pif",
    ".scr",
    ".vbs",
    ".js",
    ".jar",
    ".php",
    ".asp",
    ".aspx",
}
DANGEROUS_MIME_TYPES = {
    "application/x-executable",
    "application/x-msdownload",
    "application/x-msdos-program",
    "text/x-php",
    "application/x-php",
    "application/php",
}


def validate_file_security(file: UploadFile, content: bytes) -> bool:
    """Проверка безопасности файла"""
    if not file.filename:
        return False

    # Проверка опасных расширений
    ext = os.path.splitext(file.filename)[1].lower()
    if ext in DANGEROUS_EXTENSIONS:
        return False

    # Проверка MIME-типа
    mime_type = mimetypes.guess_type(file.filename)[0]
    if mime_type in DANGEROUS_MIME_TYPES:
        return False

    # Проверка магических байтов для основных типов файлов
    if content.startswith(b"\xff\xd8\xff") and ext in [".jpg", ".jpeg"]:  # JPEG
        return True
    elif content.startswith(b"\x89PNG\r\n\x1a\n") and ext == ".png":  # PNG
        return True
    elif content.startswith(b"%PDF") and ext == ".pdf":  # PDF
        return True
    elif content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") and ext in [
        ".doc",
        ".docx",
    ]:  # MS Office
        return True
    elif content.startswith(b"PK") and ext == ".docx":  # DOCX (ZIP-based)
        return True

    return False


def validate_file(file: UploadFile) -> bool:
    """Базовая валидация файла по расширению"""
    if not file.filename:
        return False

    # Проверка расширения
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False

    # Проверка размера (если доступно)
    if file.size and file.size > settings.MAX_FILE_SIZE:
        return False

    return True


@router.post("/upload-expense-receipt/")
async def upload_expense_receipt(
    file: UploadFile = File(...),
    current_user: Master | Employee | Administrator = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка чека расходов (только для авторизованных пользователей)"""

    try:
        # Используем новую безопасную функцию загрузки
        file_path, original_name, file_hash = await validate_and_save_file(
            file=file,
            upload_dir=settings.UPLOAD_DIR,
            subfolder="gorod/rashod",
            user_id=getattr(current_user, "id", None),
        )

        logging.info(
            f"Файл '{original_name}' успешно загружен пользователем {getattr(current_user, 'id', 'unknown')}"
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Файл успешно загружен",
                "filename": original_name,
                "file_path": file_path,
                "file_hash": file_hash,
            },
        )

    except FileSecurityError as e:
        logging.warning(f"Ошибка безопасности при загрузке файла: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")
