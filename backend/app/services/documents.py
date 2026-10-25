import re
import unicodedata
from pathlib import Path

from fastapi import UploadFile


class DocumentValidationError(ValueError):
    pass


def sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename.replace("\\", "/"))
    basename = Path(normalized).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", basename).strip(" .")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    if len(cleaned) > 255:
        suffix = Path(cleaned).suffix[:20]
        cleaned = f"{cleaned[: 255 - len(suffix)]}{suffix}"
    return cleaned


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await upload.read(64 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise DocumentValidationError(f"Document exceeds the {max_bytes // (1024 * 1024)} MB upload limit")
        chunks.append(chunk)
    return b"".join(chunks)
