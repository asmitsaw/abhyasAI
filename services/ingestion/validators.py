import os
import re
from typing import Any, List, Optional, Tuple
from werkzeug.utils import secure_filename
from config.config import Config
from services.ingestion.models import ValidationResult

# Supported file extensions mapped to source categories
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".txt": "text",
    ".md": "text",
    ".rtf": "text",
    # Presentations
    ".pptx": "presentation",
    ".ppt": "presentation",
    # Spreadsheets
    ".csv": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".xls": "spreadsheet",
    # Images
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tiff": "image",
}

# Dangerous extensions that must be rejected immediately
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".py", ".js", ".vbs", ".msi",
    ".php", ".phtml", ".cgi", ".pl", ".jar", ".dll", ".so", ".bin"
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename against path traversal, control chars, and shell injection.
    """
    if not filename:
        return "unnamed_document"

    # Remove path traversal characters
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)
    secure_name = secure_filename(cleaned)

    if not secure_name or secure_name.startswith("."):
        ext = os.path.splitext(filename)[1].lower()
        secure_name = f"doc_{os.urandom(4).hex()}{ext}"

    return secure_name


def validate_file(
    file_bytes: bytes,
    filename: str,
    max_size_mb: Optional[int] = None
) -> ValidationResult:
    """
    Validate an uploaded file against size, extension, and security rules.
    """
    max_size = (max_size_mb or Config.MAX_FILE_SIZE_MB) * 1024 * 1024
    file_size = len(file_bytes)

    if file_size == 0:
        return ValidationResult(
            is_valid=False,
            sanitized_filename=sanitize_filename(filename),
            file_extension="",
            mime_type="",
            file_size=0,
            error_message="The uploaded file is empty."
        )

    if file_size > max_size:
        return ValidationResult(
            is_valid=False,
            sanitized_filename=sanitize_filename(filename),
            file_extension=os.path.splitext(filename)[1].lower(),
            mime_type="",
            file_size=file_size,
            error_message=f"File exceeds maximum allowed size of {max_size_mb or Config.MAX_FILE_SIZE_MB} MB."
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext in DANGEROUS_EXTENSIONS:
        return ValidationResult(
            is_valid=False,
            sanitized_filename=sanitize_filename(filename),
            file_extension=ext,
            mime_type="",
            file_size=file_size,
            error_message=f"Dangerous or executable file format '{ext}' is forbidden."
        )

    if ext not in SUPPORTED_EXTENSIONS:
        return ValidationResult(
            is_valid=False,
            sanitized_filename=sanitize_filename(filename),
            file_extension=ext,
            mime_type="",
            file_size=file_size,
            error_message=f"Unsupported format: '{ext}'. Supported formats: PDF, Word, PPTX, Excel, Images, Text."
        )

    safe_name = sanitize_filename(filename)
    source_type = SUPPORTED_EXTENSIONS[ext]

    return ValidationResult(
        is_valid=True,
        sanitized_filename=safe_name,
        file_extension=ext,
        mime_type=f"application/{source_type}",
        file_size=file_size,
        error_message=None
    )


def validate_file_count(files_list: List[Any], max_allowed: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Ensure the number of uploaded files does not exceed max_allowed.
    """
    if len(files_list) == 0:
        return False, "Please upload at least one study file."
    if len(files_list) > max_allowed:
        return False, f"Maximum {max_allowed} files per session. Received {len(files_list)} files."
    return True, None
