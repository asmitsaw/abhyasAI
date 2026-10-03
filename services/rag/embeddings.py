"""
Chroma Cloud embeddings for AbhyasAI.

Dense  → ChromaCloudQwenEmbeddingFunction  (Qwen3 0.6B, semantic)
Sparse → ChromaCloudSpladeEmbeddingFunction (SPLADE, keyword precision)

Architecture (chromadb >= 1.5.x):
  - BOTH embedding functions live INSIDE the Schema:
      • Dense EF → Schema._set_vector_index_config(VectorIndexConfig(embedding_function=...))
      • Sparse EF → Schema.create_index(SparseVectorIndexConfig(embedding_function=...))
  - get_or_create_collection is called with ONLY schema= (no embedding_function kwarg)
    because passing both schema + embedding_function raises:
    "Cannot set both collection config and schema simultaneously"
  - All EFs require CHROMA_API_KEY at construction — created lazily (only when needed)
"""

import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb import Schema, SparseVectorIndexConfig, K as ChromaKey
from chromadb.api.types import VectorIndexConfig
from chromadb.utils.embedding_functions import (
    ChromaCloudQwenEmbeddingFunction,
    ChromaCloudSpladeEmbeddingFunction,
)
from chromadb.utils.embedding_functions.chroma_cloud_qwen_embedding_function import (
    ChromaCloudQwenEmbeddingModel,
)


# ---------------------------------------------------------------------------
# Lazy singleton: shared CloudClient
# ---------------------------------------------------------------------------
_cloud_client: Optional[chromadb.api.client.Client] = None


def get_cloud_client() -> chromadb.api.client.Client:
    """Return (or create) the shared Chroma Cloud client."""
    global _cloud_client
    if _cloud_client is None:
        api_key  = os.environ.get("CHROMA_API_KEY", "")
        tenant   = os.environ.get("CHROMA_TENANT",  "688bc2df-d727-4a69-9f2e-5fa46471ce1c")
        database = os.environ.get("CHROMA_DATABASE", "abhyasAI")

        if not api_key:
            raise RuntimeError(
                "CHROMA_API_KEY is not set. "
                "Copy it from https://www.trychroma.com/asmit01052005/aws-us-east-1/abhyasAI/sdk?tab=env"
            )

        _cloud_client = chromadb.CloudClient(
            tenant=tenant,
            database=database,
            api_key=api_key,
        )
        print("[ChromaCloud] Connected ✓")
    return _cloud_client


# ---------------------------------------------------------------------------
# Lazy singleton embedding functions (require CHROMA_API_KEY at construction)
# ---------------------------------------------------------------------------
_dense_ef: Optional[ChromaCloudQwenEmbeddingFunction] = None
_sparse_ef: Optional[ChromaCloudSpladeEmbeddingFunction] = None


def get_dense_ef() -> ChromaCloudQwenEmbeddingFunction:
    """Chroma Cloud Qwen3 dense embeddings. Created lazily (needs API key)."""
    global _dense_ef
    if _dense_ef is None:
        _dense_ef = ChromaCloudQwenEmbeddingFunction(
            model=ChromaCloudQwenEmbeddingModel.QWEN3_EMBEDDING_0p6B,
            task="text_matching",
        )
    return _dense_ef


def get_sparse_ef() -> ChromaCloudSpladeEmbeddingFunction:
    """Chroma Cloud SPLADE sparse embeddings. Created lazily (needs API key)."""
    global _sparse_ef
    if _sparse_ef is None:
        _sparse_ef = ChromaCloudSpladeEmbeddingFunction()
    return _sparse_ef


# ---------------------------------------------------------------------------
# Schema factory — dense + sparse both embedded in the Schema
# ---------------------------------------------------------------------------
_schema: Optional[Schema] = None


def get_hybrid_schema() -> Schema:
    """
    Build a Schema with BOTH dense and sparse indexes embedded in it.

    This Schema is passed to get_or_create_collection(schema=...) with NO
    separate embedding_function kwarg — passing both causes a server-side error.
    """
    global _schema
    if _schema is None:
        schema = Schema()

        # 1. Dense: Qwen3 EF attached to the #embedding key via VectorIndexConfig
        schema._set_vector_index_config(
            VectorIndexConfig(embedding_function=get_dense_ef())
        )

        # 2. Sparse: SPLADE EF on a separate 'sparse_embedding' key
        schema.create_index(
            config=SparseVectorIndexConfig(
                source_key=ChromaKey.DOCUMENT,
                embedding_function=get_sparse_ef(),
            ),
            key="sparse_embedding",
        )

        _schema = schema
    return _schema


# ---------------------------------------------------------------------------
# Collection naming helpers
# ---------------------------------------------------------------------------

def get_collection_name(base_name: str) -> str:
    """Stable, type-sharded collection name. e.g. 'abhyas_syllabus'"""
    return base_name.lower().replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# RAG status
# ---------------------------------------------------------------------------

def get_rag_status() -> Dict[str, Any]:
    """Returns diagnostic status of the Chroma Cloud RAG system."""
    status: Dict[str, Any] = {
        "embedding_provider": "Chroma Cloud (Qwen3 dense + SPLADE sparse)",
        "embedding_model": "qwen3-embedding-0.6B + chroma-cloud-splade",
        "vector_database": "Chroma Cloud (Hybrid RRF Search)",
        "chroma_tenant": os.environ.get("CHROMA_TENANT", "—"),
        "chroma_database": os.environ.get("CHROMA_DATABASE", "—"),
        "collections": [],
        "total_chunks_indexed": 0,
    }
    try:
        client = get_cloud_client()
        colls = client.list_collections()
        total = 0
        coll_list: List[Dict[str, Any]] = []
        for c in colls:
            count = c.count()
            total += count
            coll_list.append({"name": c.name, "count": count})
        status["collections"] = coll_list
        status["total_chunks_indexed"] = total
    except Exception as e:
        status["error"] = str(e)
    return status


def print_rag_status() -> None:
    status = get_rag_status()
    print("=" * 65)
    print("ABHYAS AI — CHROMA CLOUD RAG STATUS")
    print("=" * 65)
    print(f"Embedding Provider : {status['embedding_provider']}")
    print(f"Vector Database    : {status['vector_database']}")
    print(f"Tenant             : {status['chroma_tenant']}")
    print(f"Database           : {status['chroma_database']}")
    print(f"Total Chunks       : {status['total_chunks_indexed']}")
    for c in status.get("collections", []):
        print(f"  • {c['name']} ({c['count']} chunks)")
    if "error" in status:
        print(f"  ⚠ Error: {status['error']}")
    print("=" * 65)
