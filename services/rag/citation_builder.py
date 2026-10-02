from typing import Any, Dict, List


class Citation:
    def __init__(
        self,
        citation_id: int,
        source_name: str,
        document_type: str,
        section: str = "",
        page: str = "",
        question_number: str = "",
        year: str = "",
        marks: str = ""
    ):
        self.citation_id = citation_id
        self.source_name = source_name
        self.document_type = document_type
        self.section = section
        self.page = page
        self.question_number = question_number
        self.year = year
        self.marks = marks

    def format_inline(self) -> str:
        return f"[{self.citation_id}]"

    def format_reference(self) -> str:
        details = []
        if self.year:
            details.append(f"Year {self.year}")
        if self.question_number:
            details.append(self.question_number)
        if self.marks:
            details.append(f"{self.marks}M")
        if self.page and self.page != "1":
            details.append(f"p. {self.page}")
        if self.section and not self.question_number:
            details.append(self.section)

        detail_str = f" ({', '.join(details)})" if details else ""
        return f"[{self.citation_id}] {self.source_name}{detail_str} [{self.document_type.upper()}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.citation_id,
            "source_name": self.source_name,
            "document_type": self.document_type,
            "section": self.section,
            "page": self.page,
            "question_number": self.question_number,
            "year": self.year,
            "marks": self.marks,
            "label": self.format_reference()
        }


class CitationBuilder:
    """
    Builds structured citations from retrieved chunks.
    """

    def build_citations(self, chunks: List[Dict[str, Any]]) -> List[Citation]:
        citations = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            citations.append(Citation(
                citation_id=i,
                source_name=meta.get("source_name", "Uploaded Document"),
                document_type=meta.get("document_type", "document"),
                section=meta.get("section", ""),
                page=str(meta.get("page", "")),
                question_number=meta.get("question_number", ""),
                year=str(meta.get("year", "")),
                marks=str(meta.get("marks", ""))
            ))
        return citations
