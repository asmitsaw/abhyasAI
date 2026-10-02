import re
from typing import Any, Dict, List, Tuple


class HybridReranker:
    """
    Reranks retrieved candidate chunks using term-frequency overlap,
    exact phrase matching, question pattern relevance, and vector similarity scores.
    """

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        query_terms = set(re.findall(r'\b[a-zA-Z0-9_]{3,}\b', query.lower()))
        scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

        for item in candidates:
            doc_text = item.get("text", "").lower()
            metadata = item.get("metadata", {})
            distance = item.get("distance", 1.0)
            # Convert cosine distance to similarity (0 to 1)
            vector_sim = max(0.0, 1.0 - (distance / 2.0))

            # 1. Term overlap score (Jaccard / term recall)
            doc_terms = set(re.findall(r'\b[a-zA-Z0-9_]{3,}\b', doc_text))
            if query_terms:
                term_overlap = len(query_terms.intersection(doc_terms)) / len(query_terms)
            else:
                term_overlap = 0.0

            # 2. Exact phrase bonus
            clean_query = query.lower().strip()
            phrase_bonus = 0.3 if len(clean_query) > 5 and clean_query in doc_text else 0.0

            # 3. Metadata match bonus (e.g. topic or heading matches query term)
            heading = metadata.get("heading", "").lower()
            topic = metadata.get("topic", "").lower()
            meta_bonus = 0.2 if any(t in heading or t in topic for t in query_terms) else 0.0

            # Composite score (weights: 50% vector, 30% term overlap, 10% phrase, 10% metadata)
            final_score = (0.5 * vector_sim) + (0.3 * term_overlap) + phrase_bonus + meta_bonus
            item["rerank_score"] = round(final_score, 4)
            scored_candidates.append((final_score, item))

        # Sort descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate near-identical texts
        selected: List[Dict[str, Any]] = []
        seen_texts = set()

        for score, cand in scored_candidates:
            snippet = cand.get("text", "")[:120].strip()
            if snippet not in seen_texts:
                seen_texts.add(snippet)
                selected.append(cand)
            if len(selected) >= top_k:
                break

        return selected
