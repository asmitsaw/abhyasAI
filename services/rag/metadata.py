from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    document_id: str = Field(description="Unique hash or ID of the parent document")
    document_type: str = Field(description="syllabus|pyq|lecture|notes|question|answer")
    subject: str = Field(default="General", description="Subject name")
    module: str = Field(default="", description="Module name if applicable")
    topic: str = Field(default="", description="Specific topic or subtopic")
    source_name: str = Field(default="Uploaded Source", description="Original filename, URL, or identifier")
    page: str = Field(default="1", description="Page number or timestamp")
    question_number: str = Field(default="", description="Question identifier, e.g. Q1(a)")
    year: str = Field(default="", description="Year of paper or lecture if available")
    marks: str = Field(default="", description="Allocated marks if applicable")
    difficulty: str = Field(default="", description="Easy, Medium, Hard")
    chunk_id: str = Field(description="Unique ID for this specific chunk")
    start_index: int = Field(default=0, description="Start character offset")
    end_index: int = Field(default=0, description="End character offset")
    section: str = Field(default="", description="Document section or header")
    heading: str = Field(default="", description="Nearest heading")
    user_id: str = Field(default="", description="Authenticated user ID")
    session_id: str = Field(default="", description="Study session ID")
    file_type: str = Field(default="", description="File extension / MIME classification")
    chunk_index: int = Field(default=0, description="Sequential index in document")
    slide: str = Field(default="", description="Presentation slide number")
    sheet: str = Field(default="", description="Spreadsheet sheet name")
    snippet: str = Field(default="", description="Brief text preview")
    created_at: str = Field(default="", description="ISO timestamp")

    def to_chroma_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary with only primitive types supported by ChromaDB.
        """
        d = self.model_dump()
        # Chroma metadata values must be str, int, float or bool
        cleaned = {}
        for k, v in d.items():
            if v is None:
                cleaned[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                cleaned[k] = v
            else:
                cleaned[k] = str(v)
        return cleaned


def create_chunk_metadata(
    document_id: str,
    document_type: str,
    chunk_id: str,
    subject: str = "General",
    module: str = "",
    topic: str = "",
    source_name: str = "",
    page: str = "1",
    question_number: str = "",
    year: str = "",
    marks: str = "",
    difficulty: str = "",
    start_index: int = 0,
    end_index: int = 0,
    section: str = "",
    heading: str = ""
) -> ChunkMetadata:
    valid_types = {"syllabus", "pyq", "lecture", "notes", "question", "answer"}
    doc_type_clean = document_type.lower() if document_type.lower() in valid_types else "notes"

    return ChunkMetadata(
        document_id=document_id,
        document_type=doc_type_clean,
        subject=subject or "General",
        module=module or "",
        topic=topic or "",
        source_name=source_name or "Document",
        page=str(page or "1"),
        question_number=question_number or "",
        year=str(year or ""),
        marks=str(marks or ""),
        difficulty=difficulty or "",
        chunk_id=chunk_id,
        start_index=start_index,
        end_index=end_index,
        section=section or "",
        heading=heading or ""
    )
