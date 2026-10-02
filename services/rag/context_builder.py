from typing import Any, Dict, List
from services.rag.citation_builder import Citation


class ContextBuilder:
    """
    Compresses and formats retrieved chunks into a numbered, citation-ready context block
    for grounding LLM responses.
    """

    def build_context(self, chunks: List[Dict[str, Any]], citations: List[Citation]) -> str:
        if not chunks:
            return "No relevant source material found in the indexed repository."

        blocks = []
        for i, (chunk, citation) in enumerate(zip(chunks, citations), 1):
            source_label = citation.format_reference()
            text = chunk.get("text", "").strip()
            # Truncate if individual chunk is excessively large
            if len(text) > 1200:
                text = text[:1200] + " ... [content truncated]"
            blocks.append(f"--- SOURCE CONTEXT {source_label} ---\n{text}")

        return "\n\n".join(blocks)

    def get_grounding_system_instruction(self) -> str:
        return (
            "You are Abhyas AI, the University Exam Intelligence & Study Sidekick.\n"
            "STRICT GROUNDING & CITATION RULES:\n"
            "1. Ground your response directly in the provided source context chunks labeled with [1], [2], etc.\n"
            "2. Whenever citing facts, cite the source using inline brackets like [1] or [2].\n"
            "3. If the provided source material lacks sufficient evidence, state clearly:\n"
            "   'I couldn't find enough evidence in the uploaded material.'\n"
            "4. Distinguish clearly between:\n"
            "   - [SOURCE FACT]: directly stated in the syllabus, past paper, or lecture.\n"
            "   - [AI INFERENCE]: logical conclusion or synthesis.\n"
            "   - [RECOMMENDATION]: targeted advice for the student's preparation.\n"
            "5. Never claim that a question WILL definitely appear on the exam. Use phrasing such as:\n"
            "   'historically frequent', 'high historical relevance', or 'observed in uploaded PYQs'.\n"
            "6. Keep explanations clear, structured, and easy for university students to absorb."
        )
