import os
import pytest
from services.rag.metadata import create_chunk_metadata, ChunkMetadata
from services.rag.chunking import StructureAwareChunker
from services.rag.embeddings import AbhyasEmbeddingFunction, get_collection_name
from services.rag.ingestion import UniversalIngestionService
from services.rag.query_router import QueryRouter, QueryType
from services.rag.citation_builder import CitationBuilder, Citation
from services.rag.context_builder import ContextBuilder
from services.rag.reranker import HybridReranker
from services.rag.retriever import HybridRetriever
from services.rag.evaluation import RAGEvaluator


def test_chunk_metadata_schema():
    meta = create_chunk_metadata(
        document_id="doc_123",
        document_type="syllabus",
        chunk_id="chunk_01",
        subject="Operating Systems",
        module="Module 1: Process Management",
        topic="CPU Scheduling",
        source_name="OS_Syllabus.pdf",
        page="2",
        marks="10",
        difficulty="Medium"
    )
    assert meta.document_id == "doc_123"
    assert meta.document_type == "syllabus"
    assert meta.subject == "Operating Systems"

    chroma_dict = meta.to_chroma_dict()
    assert isinstance(chroma_dict["page"], str)
    assert chroma_dict["page"] == "2"
    assert chroma_dict["document_id"] == "doc_123"


def test_structure_aware_chunking_syllabus():
    chunker = StructureAwareChunker(chunk_size=300, chunk_overlap=50)
    sample_syllabus = """
MODULE 1: PROCESS MANAGEMENT
Process states, process scheduling, interprocess communication, threads.

MODULE 2: MEMORY MANAGEMENT
Paging, segmentation, virtual memory, demand paging, thrashing.
"""
    chunks = chunker.chunk_document(
        text=sample_syllabus,
        document_id="syl_01",
        document_type="syllabus",
        source_name="syllabus.txt",
        subject="OS"
    )
    assert len(chunks) >= 2
    modules = [meta.module for _, meta in chunks]
    assert any("MODULE 1" in m for m in modules)
    assert any("MODULE 2" in m for m in modules)


def test_structure_aware_chunking_pyq():
    chunker = StructureAwareChunker(chunk_size=400, chunk_overlap=60)
    sample_pyq = """
UNIVERSITY EXAM 2025
Q1. Define thread and state differences from process. (5 Marks)
Q2. Explain LRU page replacement algorithm. (10 Marks)
Q3. Solve Banker's algorithm matrix problem. (10 Marks)
"""
    chunks = chunker.chunk_document(
        text=sample_pyq,
        document_id="pyq_01",
        document_type="pyq",
        source_name="pyq_2025.txt",
        subject="OS",
        year="2025"
    )
    assert len(chunks) >= 3
    q_texts = [txt for txt, _ in chunks]
    assert any("Q1" in t or "thread" in t for t in q_texts)
    assert any("Q2" in t or "LRU" in t for t in q_texts)


def test_embeddings_deterministic_fallback():
    embed_fn = AbhyasEmbeddingFunction()
    docs = ["Process scheduling in Operating Systems", "Virtual memory and paging mechanisms"]
    vectors = embed_fn(docs)
    assert len(vectors) == 2
    assert len(vectors[0]) in (768, 1024, 3072)
    assert len(vectors[1]) in (768, 1024, 3072)
    # Consistent output for identical string
    vectors_repeat = embed_fn(docs)
    import numpy as np
    assert np.allclose(vectors[0], vectors_repeat[0], atol=1e-2)


def test_query_router_classification():
    router = QueryRouter()
    assert router.route_query("What topics are important for the exam?") == QueryType.EXAM_PATTERN
    assert router.route_query("Was deadlock asked in 2025 PYQ?") == QueryType.PYQ
    assert router.route_query("What should I study now?") == QueryType.STUDY_PLAN
    assert router.route_query("Ask me viva questions on semaphores") == QueryType.VIVA
    assert router.route_query("Evaluate my answer for 10 marks") == QueryType.ANSWER_EVALUATION
    assert router.route_query("Explain virtual memory in simple terms") == QueryType.TOPIC


def test_citation_builder():
    builder = CitationBuilder()
    mock_chunks = [
        {
            "text": "Round Robin uses time slices.",
            "metadata": {
                "source_name": "PYQ_2024.pdf",
                "document_type": "pyq",
                "question_number": "Q3(a)",
                "year": "2024",
                "marks": "10"
            }
        },
        {
            "text": "Virtual memory allows large address space.",
            "metadata": {
                "source_name": "Syllabus_2026.pdf",
                "document_type": "syllabus",
                "section": "Module 2",
                "page": "3"
            }
        }
    ]
    citations = builder.build_citations(mock_chunks)
    assert len(citations) == 2
    assert citations[0].citation_id == 1
    assert "PYQ_2024" in citations[0].format_reference()
    assert "[1]" in citations[0].format_inline()
    assert "[PYQ]" in citations[0].format_reference()


def test_context_builder():
    c_builder = ContextBuilder()
    citations = [
        Citation(citation_id=1, source_name="PYQ 2024", document_type="pyq", year="2024", question_number="Q1")
    ]
    chunks = [{"text": "Paging reduces external fragmentation."}]
    context_str = c_builder.build_context(chunks, citations)
    assert "--- SOURCE CONTEXT [1] PYQ 2024" in context_str
    assert "Paging reduces external fragmentation" in context_str

    sys_inst = c_builder.get_grounding_system_instruction()
    assert "STRICT GROUNDING & CITATION RULES" in sys_inst
    assert "historically frequent" in sys_inst


def test_hybrid_reranker():
    reranker = HybridReranker()
    candidates = [
        {
            "text": "File systems store directory structures on disk.",
            "metadata": {"heading": "File System Overview"},
            "distance": 0.8
        },
        {
            "text": "CPU scheduling algorithms like Round Robin allocate quantum timeslices to processes.",
            "metadata": {"heading": "Round Robin CPU Scheduling"},
            "distance": 0.2
        }
    ]
    reranked = reranker.rerank(query="What is Round Robin CPU scheduling?", candidates=candidates, top_k=2)
    assert len(reranked) == 2
    # The CPU scheduling chunk must rank higher due to term and vector similarity
    assert "Round Robin" in reranked[0]["text"]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_universal_ingestion_and_deduplication():
    ingestion = UniversalIngestionService()
    test_text = "MODULE 1: Process Concurrency\nMutual exclusion and semaphores."
    
    # Ingest once
    res1 = ingestion.ingest_raw_text(
        text=test_text,
        title="Concurrency_Notes.txt",
        document_type="notes",
        subject="Operating Systems"
    )
    assert res1["status"] in ["success", "already_indexed"]
    doc_hash = res1["document_id"]

    # Ingest identical content again - must detect duplicate and NOT crash or duplicate
    res2 = ingestion.ingest_raw_text(
        text=test_text,
        title="Concurrency_Notes.txt",
        document_type="notes",
        subject="Operating Systems"
    )
    assert res2["status"] == "already_indexed"
    assert res2["document_id"] == doc_hash
