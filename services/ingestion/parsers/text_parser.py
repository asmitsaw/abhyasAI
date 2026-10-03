import os
from typing import List
from services.document_service import clean_and_normalize_text
from services.ingestion.models import ExtractedChunk, NormalizedDocument


def parse_text(file_bytes: bytes, filename: str) -> NormalizedDocument:
    """
    Parse plaintext, Markdown, and RTF files with encoding safety.
    """
    ext = os.path.splitext(filename)[1].lower()
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = file_bytes.decode("latin-1")
        except Exception:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

    clean_text = clean_and_normalize_text(raw_text)

    # Approximate page division (approx 1500 chars per page)
    blocks = clean_text.split("\n\n")
    chunks: List[ExtractedChunk] = []
    current_page = 1
    char_count = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        chunks.append(ExtractedChunk(
            text=block,
            page=current_page,
            section=f"Section {len(chunks) + 1}",
            heading=block[:50].split("\n")[0],
            source_type="text"
        ))
        char_count += len(block)
        if char_count > 1500:
            current_page += 1
            char_count = 0

    return NormalizedDocument(
        text=clean_text,
        original_filename=filename,
        source_type="text",
        mime_type="text/plain",
        file_extension=ext or ".txt",
        file_size=len(file_bytes),
        page_count=current_page,
        chunks=chunks
    )
