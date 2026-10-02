import os
import re
from typing import Any, Dict, List, Tuple
from services.rag.metadata import ChunkMetadata, create_chunk_metadata


class StructureAwareChunker:
    """
    Structure-aware chunker tailored for educational documents:
    - Syllabus: Module -> Topic -> Subtopic
    - PYQs: Year -> Paper -> Section -> Question
    - Lectures: Semantic time/topic sections
    - Notes: Headings (# / Section) -> Paragraph groups
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", 800))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", 120))

    def chunk_document(
        self,
        text: str,
        document_id: str,
        document_type: str,
        source_name: str,
        subject: str = "General",
        year: str = ""
    ) -> List[Tuple[str, ChunkMetadata]]:
        doc_type = document_type.lower()
        if doc_type == "syllabus":
            return self._chunk_syllabus(text, document_id, source_name, subject)
        elif doc_type == "pyq":
            return self._chunk_pyq(text, document_id, source_name, subject, year)
        elif doc_type == "lecture":
            return self._chunk_lecture(text, document_id, source_name, subject)
        else:
            return self._chunk_notes(text, document_id, doc_type, source_name, subject)

    def _chunk_syllabus(
        self,
        text: str,
        document_id: str,
        source_name: str,
        subject: str
    ) -> List[Tuple[str, ChunkMetadata]]:
        chunks: List[Tuple[str, ChunkMetadata]] = []
        # Split by Module / Unit patterns
        module_pattern = re.compile(r'(?i)(?:^|\n)(MODULE\s+\d+|UNIT\s+\d+|CHAPTER\s+\d+[:\s\-\w]+)', re.MULTILINE)
        splits = list(module_pattern.finditer(text))

        if not splits:
            return self._fallback_sliding_window(text, document_id, "syllabus", source_name, subject)

        for i, match in enumerate(splits):
            module_name = match.group(1).strip()
            start_pos = match.start()
            end_pos = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            module_text = text[start_pos:end_pos].strip()

            # Split module into subtopic blocks if large
            if len(module_text) <= self.chunk_size:
                chunk_id = f"{document_id}_m{i+1}_1"
                meta = create_chunk_metadata(
                    document_id=document_id,
                    document_type="syllabus",
                    chunk_id=chunk_id,
                    subject=subject,
                    module=module_name,
                    source_name=source_name,
                    start_index=start_pos,
                    end_index=end_pos,
                    section=module_name,
                    heading=module_name
                )
                chunks.append((module_text, meta))
            else:
                # Sub-chunk by paragraphs or topics
                sub_chunks = self._sliding_sub_chunks(module_text, start_pos)
                for sub_i, (sub_txt, s_idx, e_idx) in enumerate(sub_chunks):
                    chunk_id = f"{document_id}_m{i+1}_{sub_i+1}"
                    meta = create_chunk_metadata(
                        document_id=document_id,
                        document_type="syllabus",
                        chunk_id=chunk_id,
                        subject=subject,
                        module=module_name,
                        source_name=source_name,
                        start_index=s_idx,
                        end_index=e_idx,
                        section=module_name,
                        heading=module_name
                    )
                    chunks.append((sub_txt, meta))

        return chunks

    def _chunk_pyq(
        self,
        text: str,
        document_id: str,
        source_name: str,
        subject: str,
        default_year: str = ""
    ) -> List[Tuple[str, ChunkMetadata]]:
        chunks: List[Tuple[str, ChunkMetadata]] = []
        # Extract year if present in header
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', text[:500])
        year_val = year_match.group(1) if year_match else default_year

        # Split by question pattern: Q1, Q.1, Question 1, 1(a), etc.
        q_pattern = re.compile(r'(?i)(?:^|\n)(?:Section\s+[A-Z]|Part\s+[A-Z]|Q(?:uestion)?\.?\s*\d+[\(\)\w]*|\(\w\))', re.MULTILINE)
        matches = list(q_pattern.finditer(text))

        if not matches or len(matches) < 2:
            return self._fallback_sliding_window(text, document_id, "pyq", source_name, subject, year=year_val)

        for i, match in enumerate(matches):
            q_header = match.group(0).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            q_text = text[start_pos:end_pos].strip()

            # Detect marks if present e.g. [5 Marks], (10M), 6 Marks
            marks_match = re.search(r'\[?\(?(\d{1,2})\s*(?:Marks?|M|marks?)\]?\)?', q_text, re.IGNORECASE)
            marks_val = marks_match.group(1) if marks_match else ""

            chunk_id = f"{document_id}_q{i+1}"
            meta = create_chunk_metadata(
                document_id=document_id,
                document_type="pyq",
                chunk_id=chunk_id,
                subject=subject,
                source_name=source_name,
                question_number=q_header,
                year=year_val,
                marks=marks_val,
                start_index=start_pos,
                end_index=end_pos,
                section="Question Paper",
                heading=q_header
            )
            chunks.append((q_text, meta))

        return chunks

    def _chunk_lecture(
        self,
        text: str,
        document_id: str,
        source_name: str,
        subject: str
    ) -> List[Tuple[str, ChunkMetadata]]:
        # Transcripts often have timestamps [00:01:23] or flow continuously
        chunks: List[Tuple[str, ChunkMetadata]] = []
        raw_chunks = self._sliding_sub_chunks(text, 0)
        for i, (chunk_text, start_idx, end_idx) in enumerate(raw_chunks):
            chunk_id = f"{document_id}_lec_{i+1}"
            meta = create_chunk_metadata(
                document_id=document_id,
                document_type="lecture",
                chunk_id=chunk_id,
                subject=subject,
                source_name=source_name,
                page=str((i // 2) + 1),
                start_index=start_idx,
                end_index=end_idx,
                section=f"Timestamp Block {i+1}",
                heading=f"Lecture Segment {i+1}"
            )
            chunks.append((chunk_text, meta))
        return chunks

    def _chunk_notes(
        self,
        text: str,
        document_id: str,
        document_type: str,
        source_name: str,
        subject: str
    ) -> List[Tuple[str, ChunkMetadata]]:
        chunks: List[Tuple[str, ChunkMetadata]] = []
        # Split by markdown headers (#, ##, ###) or page separators (--- PAGE 1 ---)
        header_pattern = re.compile(r'(?:^|\n)(#{1,4}\s+[\w\s\(\)\-]+|---\s*PAGE\s*\d+\s*---)', re.MULTILINE)
        matches = list(header_pattern.finditer(text))

        if not matches:
            return self._fallback_sliding_window(text, document_id, document_type, source_name, subject)

        for i, match in enumerate(matches):
            heading_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start_pos:end_pos].strip()

            page_match = re.search(r'PAGE\s*(\d+)', heading_text, re.IGNORECASE)
            page_val = page_match.group(1) if page_match else "1"

            if len(section_text) <= self.chunk_size:
                chunk_id = f"{document_id}_n{i+1}_1"
                meta = create_chunk_metadata(
                    document_id=document_id,
                    document_type=document_type,
                    chunk_id=chunk_id,
                    subject=subject,
                    source_name=source_name,
                    page=page_val,
                    start_index=start_pos,
                    end_index=end_pos,
                    section=heading_text,
                    heading=heading_text
                )
                chunks.append((section_text, meta))
            else:
                sub_chunks = self._sliding_sub_chunks(section_text, start_pos)
                for sub_i, (sub_txt, s_idx, e_idx) in enumerate(sub_chunks):
                    chunk_id = f"{document_id}_n{i+1}_{sub_i+1}"
                    meta = create_chunk_metadata(
                        document_id=document_id,
                        document_type=document_type,
                        chunk_id=chunk_id,
                        subject=subject,
                        source_name=source_name,
                        page=page_val,
                        start_index=s_idx,
                        end_index=e_idx,
                        section=heading_text,
                        heading=heading_text
                    )
                    chunks.append((sub_txt, meta))
        return chunks

    def _sliding_sub_chunks(self, text: str, base_offset: int) -> List[Tuple[str, int, int]]:
        chunks = []
        start = 0
        text_len = len(text)
        step = max(1, self.chunk_size - self.chunk_overlap)

        while start < text_len:
            end = min(text_len, start + self.chunk_size)
            # Find nearest newline or space to prevent cutting words
            if end < text_len:
                break_point = text.rfind("\n", start + self.chunk_size // 2, end)
                if break_point != -1:
                    end = break_point + 1
                else:
                    space_point = text.rfind(" ", start + self.chunk_size // 2, end)
                    if space_point != -1:
                        end = space_point + 1

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append((chunk_content, base_offset + start, base_offset + end))

            if end >= text_len:
                break
            start += step
        return chunks

    def _fallback_sliding_window(
        self,
        text: str,
        document_id: str,
        document_type: str,
        source_name: str,
        subject: str,
        year: str = ""
    ) -> List[Tuple[str, ChunkMetadata]]:
        sub_chunks = self._sliding_sub_chunks(text, 0)
        results = []
        for i, (chunk_txt, s_idx, e_idx) in enumerate(sub_chunks):
            chunk_id = f"{document_id}_chunk_{i+1}"
            meta = create_chunk_metadata(
                document_id=document_id,
                document_type=document_type,
                chunk_id=chunk_id,
                subject=subject,
                source_name=source_name,
                year=year,
                start_index=s_idx,
                end_index=e_idx,
                section="General Content",
                heading=f"Section {i+1}"
            )
            results.append((chunk_txt, meta))
        return results
