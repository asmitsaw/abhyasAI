from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractedChunk(BaseModel):
    text: str
    page: int = 1
    section: str = ""
    heading: str = ""
    slide: Optional[int] = None
    sheet: Optional[str] = None
    source_type: str = "document"


class NormalizedDocument(BaseModel):
    text: str
    original_filename: str
    source_type: str
    mime_type: str = ""
    file_extension: str = ""
    file_size: int = 0
    page_count: int = 1
    chunks: List[ExtractedChunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ValidationResult(BaseModel):
    is_valid: bool
    sanitized_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    error_message: Optional[str] = None
