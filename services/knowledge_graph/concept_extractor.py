import re
from typing import Any, Dict, List, Optional
from services.llm.provider_factory import get_llm_provider


class ConceptExtractor:
    """
    Extracts atomic academic concepts, subtopics, and prerequisite dependencies
    from syllabus texts and lecture materials.
    """

    def __init__(self):
        self.provider = get_llm_provider()

    def extract_concepts_from_module(
        self,
        module_name: str,
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        extracted = []
        for t in topics:
            clean_topic = t.strip()
            # Split subtopics by comma, parentheses or semicolon if detailed
            sub_matches = re.split(r'[,;()]+', clean_topic)
            subtopics = [s.strip() for s in sub_matches if len(s.strip()) > 3]

            extracted.append({
                "module": module_name,
                "topic": clean_topic,
                "concepts": subtopics or [clean_topic]
            })
        return extracted
