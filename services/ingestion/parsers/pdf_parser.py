import io
from typing import List
from pypdf import PdfReader
from services.document_service import clean_and_normalize_text
from services.ingestion.models import ExtractedChunk, NormalizedDocument


def parse_pdf(file_bytes: bytes, filename: str) -> NormalizedDocument:
    """
    Extract text page-by-page from PDF binary bytes.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    page_count = len(reader.pages)
    chunks: List[ExtractedChunk] = []
    full_text_blocks = []

    for page_idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        clean_page = clean_and_normalize_text(raw_text)
        if clean_page:
            full_text_blocks.append(f"--- PAGE {page_idx} ---\n{clean_page}")
            chunks.append(ExtractedChunk(
                text=clean_page,
                page=page_idx,
                section=f"Page {page_idx}",
                heading=f"PDF Page {page_idx}",
                source_type="pdf"
            ))

    all_text = "\n\n".join(full_text_blocks)
    return NormalizedDocument(
        text=all_text,
        original_filename=filename,
        source_type="pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=len(file_bytes),
        page_count=page_count,
        chunks=chunks
    )
