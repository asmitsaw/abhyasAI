from typing import Any, Dict, List, Optional
from services.llm.provider_factory import get_llm_provider
from services.rag.citation_builder import CitationBuilder
from services.rag.context_builder import ContextBuilder
from services.rag.ingestion import UniversalIngestionService
from services.rag.retriever import HybridRetriever


class RAGPipeline:
    """
    End-to-end RAG orchestrator for AbhyasAI:
    Query -> Classification -> Hybrid Retrieval -> Reranking ->
    Citation Tracking -> Context Grounding -> LLM Synthesis.
    """

    def __init__(
        self,
        ingestion_service: Optional[UniversalIngestionService] = None,
        retriever: Optional[HybridRetriever] = None
    ):
        self.ingestion = ingestion_service or UniversalIngestionService()
        self.retriever = retriever or HybridRetriever(self.ingestion)
        self.citation_builder = CitationBuilder()
        self.context_builder = ContextBuilder()

    def query(
        self,
        question: str,
        subject: Optional[str] = "General",
        module: Optional[str] = None,
        document_type: Optional[str] = None,
        top_k: int = 5,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        # 1. Retrieve & Rerank Chunks
        retrieval_res = self.retriever.retrieve(
            query=question,
            subject=subject,
            module=module,
            document_type=document_type,
            top_k=top_k
        )
        chunks = retrieval_res.get("chunks", [])
        query_type = retrieval_res.get("query_type", "GENERAL_TUTOR")

        # 2. Build Citations & Context
        citations = self.citation_builder.build_citations(chunks)
        context_str = self.context_builder.build_context(chunks, citations)
        sys_instruction = self.context_builder.get_grounding_system_instruction()

        # 3. Formulate Prompt
        prompt = (
            f"Query Classification: {query_type}\n"
            f"Target Subject: {subject or 'General'}\n\n"
            f"=== RETRIEVED SOURCE EVIDENCE ===\n"
            f"{context_str}\n"
            f"=================================\n\n"
            f"Student Question:\n{question}\n\n"
            f"Provide a clear, evidence-backed response adhering to the citation rules."
        )

        # 4. Generate with LLM Provider
        provider = get_llm_provider()
        answer = provider.generate(
            prompt=prompt,
            system_instruction=sys_instruction,
            temperature=0.3,
            use_reasoning=use_reasoning
        )

        return {
            "query": question,
            "answer": answer,
            "query_type": query_type,
            "citations": [c.to_dict() for c in citations],
            "evidence_found": len(chunks) > 0,
            "sources_used": list({c.source_name for c in citations}),
            "retrieval_count": len(chunks)
        }


_global_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _global_rag_pipeline
    if _global_rag_pipeline is None:
        _global_rag_pipeline = RAGPipeline()
    return _global_rag_pipeline
