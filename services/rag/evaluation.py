from typing import Any, Dict, List
from services.rag.rag_pipeline import RAGPipeline


# Standard evaluation benchmark questions for operating systems / academic topics
EVALUATION_DATASET = [
    {
        "question": "What is Round Robin CPU scheduling and what is time quantum?",
        "expected_topic": "Process Management",
        "expected_keywords": ["round robin", "quantum", "cpu", "scheduling"]
    },
    {
        "question": "What are the four necessary conditions for a deadlock to occur?",
        "expected_topic": "Deadlocks",
        "expected_keywords": ["mutual exclusion", "hold and wait", "no preemption", "circular wait"]
    },
    {
        "question": "Explain paging and page fault in virtual memory.",
        "expected_topic": "Memory Management",
        "expected_keywords": ["paging", "page fault", "frame", "virtual"]
    }
]


class RAGEvaluator:
    """
    Evaluates RAG pipeline performance:
    - Retrieval Relevance
    - Citation Correctness
    - Answer Groundedness
    - Context Utilization
    """

    def __init__(self, pipeline: RAGPipeline = None):
        self.pipeline = pipeline or RAGPipeline()

    def evaluate_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        query = item["question"]
        expected_keywords = item.get("expected_keywords", [])

        result = self.pipeline.query(question=query, top_k=4)
        answer = result.get("answer", "").lower()
        citations = result.get("citations", [])

        # 1. Retrieval relevance: at least one chunk or citation returned
        retrieval_relevance = 1.0 if result.get("evidence_found") else 0.0

        # 2. Citation correctness: answer contains citation bracket [1] or similar
        has_citations = any(f"[{c['id']}]" in result.get("answer", "") for c in citations)
        citation_correctness = 1.0 if has_citations or len(citations) == 0 else 0.5

        # 3. Groundedness / Keyword recall
        matched_keywords = [kw for kw in expected_keywords if kw.lower() in answer]
        keyword_recall = len(matched_keywords) / max(1, len(expected_keywords))

        # 4. Hallucination guard: checks if system properly acknowledges missing info
        acknowledged_insufficient = "not enough evidence" in answer or "couldn't find enough" in answer

        composite_score = round((retrieval_relevance * 0.3) + (citation_correctness * 0.3) + (keyword_recall * 0.4), 2)

        return {
            "question": query,
            "retrieval_relevance": retrieval_relevance,
            "citation_correctness": citation_correctness,
            "keyword_recall": round(keyword_recall, 2),
            "matched_keywords": matched_keywords,
            "composite_score": composite_score,
            "acknowledged_insufficient": acknowledged_insufficient
        }

    def run_benchmark(self, dataset: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        items = dataset or EVALUATION_DATASET
        results = [self.evaluate_item(item) for item in items]
        avg_score = round(sum(r["composite_score"] for r in results) / max(1, len(results)), 2)
        avg_recall = round(sum(r["keyword_recall"] for r in results) / max(1, len(results)), 2)

        return {
            "total_evaluated": len(results),
            "average_score": avg_score,
            "average_keyword_recall": avg_recall,
            "item_results": results
        }
