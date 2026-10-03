import os
import time
import uuid
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from services.ingestion.models import NormalizedDocument, ValidationResult
from services.ingestion.validators import (
    validate_file,
    validate_file_count,
    sanitize_filename,
    SUPPORTED_EXTENSIONS
)
from services.ingestion.parsers.pdf_parser import parse_pdf
from services.ingestion.parsers.docx_parser import parse_docx
from services.ingestion.parsers.pptx_parser import parse_pptx
from services.ingestion.parsers.spreadsheet_parser import parse_spreadsheet
from services.ingestion.parsers.text_parser import parse_text
from services.ingestion.parsers.image_parser import parse_image

from services.rag.chunking import StructureAwareChunker
from services.rag.metadata import ChunkMetadata, create_chunk_metadata
from services.rag.embeddings import get_cloud_client, get_hybrid_schema, get_collection_name
from services.supabase_service import get_supabase_service

logger = logging.getLogger("abhyas_ai.ingestion.manager")


class IngestionManager:
    """
    Production-grade multi-file ingestion pipeline for AbhyasAI.
    Coordinates: Validation -> Extraction -> Normalization -> Structure Chunking ->
    Chroma Cloud Upsert -> Supabase Relational Persistence -> Study Session State Transition.
    """

    def __init__(self):
        self.chunker = StructureAwareChunker(chunk_size=800, chunk_overlap=120)
        self.supabase = get_supabase_service()
        self._client = None
        self._schema = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_cloud_client()
        return self._client

    @property
    def schema(self):
        if self._schema is None:
            self._schema = get_hybrid_schema()
        return self._schema

    def get_or_create_collection(self, collection_type: str = "documents"):
        name = get_collection_name(f"abhyas_{collection_type.lower()}")
        return self.client.get_or_create_collection(
            name=name,
            schema=self.schema,
        )

    def parse_file(self, file_bytes: bytes, filename: str) -> NormalizedDocument:
        """Dispatch file bytes to the appropriate format parser."""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return parse_pdf(file_bytes, filename)
        elif ext in [".docx", ".doc"]:
            return parse_docx(file_bytes, filename)
        elif ext in [".pptx", ".ppt"]:
            return parse_pptx(file_bytes, filename)
        elif ext in [".csv", ".xlsx", ".xls"]:
            return parse_spreadsheet(file_bytes, filename)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            return parse_image(file_bytes, filename)
        elif ext in [".txt", ".md", ".rtf"]:
            return parse_text(file_bytes, filename)
        else:
            # Fallback to plain text decoding
            return parse_text(file_bytes, filename)

    def ingest_session_files(
        self,
        session_id: str,
        user_id: str,
        files_data: List[Tuple[str, bytes]],
        subject_name: str = "General",
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingests up to 3 files for a specific study session.
        Enforces tenant isolation, idempotency, and transactional consistency.
        """
        start_time = time.perf_counter()

        # 1. Validate File Count
        count_ok, count_err = validate_file_count(files_data, max_allowed=3)
        if not count_ok:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_FILE_COUNT",
                    "message": count_err
                }
            }

        # 2. Mark Session as PROCESSING
        self.supabase.update_study_session_status(session_id, "PROCESSING", user_token=user_token)

        successful_docs = 0
        failed_docs = 0
        total_chunks = 0
        document_results = []
        errors = []

        collection = self.get_or_create_collection("documents")

        for orig_filename, file_bytes in files_data:
            # 3. Validate Each File
            val_res: ValidationResult = validate_file(file_bytes, orig_filename)
            if not val_res.is_valid:
                failed_docs += 1
                errors.append(f"{orig_filename}: {val_res.error_message}")
                document_results.append({
                    "filename": orig_filename,
                    "status": "FAILED",
                    "error": val_res.error_message,
                    "chunks": 0
                })
                continue

            # Deterministic document hash based on session, filename, and bytes
            doc_id = hashlib.sha256(f"{session_id}:{val_res.sanitized_filename}".encode("utf-8") + file_bytes).hexdigest()[:32]

            try:
                # 4. Extract & Normalize Document Content
                normalized: NormalizedDocument = self.parse_file(file_bytes, val_res.sanitized_filename)
                if not normalized.text or not normalized.text.strip():
                    raise ValueError("Document yielded no readable text content.")

                # Register in Supabase as PENDING
                self.supabase.create_document_record(
                    document_id=doc_id,
                    session_id=session_id,
                    user_id=user_id,
                    original_filename=val_res.sanitized_filename,
                    file_size=val_res.file_size,
                    mime_type=val_res.mime_type,
                    file_extension=val_res.file_extension,
                    source_type=normalized.source_type,
                    page_count=normalized.page_count,
                    status="PROCESSING",
                    user_token=user_token
                )

                # 5. Structure-Aware Chunking
                chunk_tuples = self.chunker.chunk_document(
                    text=normalized.text,
                    document_id=doc_id,
                    document_type="notes",
                    source_name=val_res.sanitized_filename,
                    subject=subject_name
                )
                if not chunk_tuples:
                    raise ValueError("Document produced 0 valid chunks.")

                # 6. Build Multi-Tenant Metadata with Scoping
                ids = []
                documents = []
                metadatas = []

                for idx, (chunk_txt, chunk_meta) in enumerate(chunk_tuples):
                    # Deterministic unique chunk ID
                    c_id = f"{session_id}:{doc_id}:chunk:{idx}"
                    ids.append(c_id)
                    documents.append(chunk_txt)

                    meta_dict = chunk_meta.to_chroma_dict()
                    meta_dict["user_id"] = str(user_id)
                    meta_dict["session_id"] = str(session_id)
                    meta_dict["document_id"] = doc_id
                    meta_dict["filename"] = val_res.sanitized_filename
                    meta_dict["source_type"] = normalized.source_type
                    meta_dict["file_type"] = val_res.file_extension
                    meta_dict["chunk_id"] = c_id
                    meta_dict["chunk_index"] = idx
                    meta_dict["snippet"] = chunk_txt[:250].replace("\n", " ")

                    metadatas.append(meta_dict)

                # 7. Upsert to Chroma Cloud
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

                # 8. Update Document Record to INDEXED
                self.supabase.update_document_status(
                    document_id=doc_id,
                    status="INDEXED",
                    chunk_count=len(ids),
                    user_token=user_token
                )

                successful_docs += 1
                total_chunks += len(ids)
                document_results.append({
                    "document_id": doc_id,
                    "filename": val_res.sanitized_filename,
                    "status": "INDEXED",
                    "chunks": len(ids),
                    "pages": normalized.page_count
                })

            except Exception as doc_err:
                failed_docs += 1
                err_msg = str(doc_err)
                errors.append(f"{val_res.sanitized_filename}: {err_msg}")
                self.supabase.create_document_record(
                    document_id=doc_id,
                    session_id=session_id,
                    user_id=user_id,
                    original_filename=val_res.sanitized_filename,
                    file_size=val_res.file_size,
                    mime_type=val_res.mime_type,
                    file_extension=val_res.file_extension,
                    source_type="document",
                    status="FAILED",
                    error_message=err_msg,
                    user_token=user_token
                )
                document_results.append({
                    "document_id": doc_id,
                    "filename": val_res.sanitized_filename,
                    "status": "FAILED",
                    "error": err_msg,
                    "chunks": 0
                })

        # 9. Compute Final Session Status (Never READY if Chroma failed)
        if successful_docs > 0 and failed_docs == 0:
            final_status = "READY"
        elif successful_docs > 0 and failed_docs > 0:
            final_status = "PARTIAL"
        else:
            final_status = "FAILED"

        self.supabase.update_study_session_status(session_id, final_status, user_token=user_token)

        duration = round(time.perf_counter() - start_time, 2)
        logger.info(f"Ingestion finished for session {session_id}: status={final_status}, chunks={total_chunks}, duration={duration}s")

        return {
            "success": successful_docs > 0,
            "session_id": session_id,
            "status": final_status,
            "total_files": len(files_data),
            "successful_files": successful_docs,
            "failed_files": failed_docs,
            "total_chunks_indexed": total_chunks,
            "duration_seconds": duration,
            "documents": document_results,
            "errors": errors
        }


_global_ingestion_manager: Optional[IngestionManager] = None


def get_ingestion_manager() -> IngestionManager:
    global _global_ingestion_manager
    if _global_ingestion_manager is None:
        _global_ingestion_manager = IngestionManager()
    return _global_ingestion_manager
