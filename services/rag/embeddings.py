import os
import hashlib
from typing import List, Dict, Any
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from services.llm.provider_factory import get_llm_provider


class AbhyasEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDB compatible EmbeddingFunction wrapping configured LLM embeddings
    with deterministic fallback vectors to ensure collections never crash.
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        self.dimension = 3072

    def name(self) -> str:
        return f"abhyas_{self.model_name.replace('-', '_')}"

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []

        try:
            provider = get_llm_provider()
            vectors = provider.embed(texts=list(input), model=self.model_name)
            if vectors and len(vectors) == len(input):
                return vectors
        except Exception as error:
            print(f"[EmbeddingFunction] External embedding API error: {error}. Falling back to deterministic pseudo-embeddings.")

        # Fallback to deterministic hashed embeddings
        return [self._deterministic_vector(doc) for doc in input]

    def _deterministic_vector(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode('utf-8')).digest()
        # Create vector normalized between -1.0 and 1.0
        expanded = (digest * 96)[:self.dimension]
        return [((b - 128) / 128.0) for b in expanded]


def get_collection_name(base_name: str) -> str:
    """
    Generate versioned collection name keyed to the embedding model to avoid mixing models.
    e.g., 'abhyas_syllabus_gemini_embedding_001_v1'
    """
    model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    sanitized_model = model_name.replace("-", "_").replace(".", "_").lower()
    return f"{base_name}_{sanitized_model}_v1"


def get_rag_status() -> Dict[str, Any]:
    """
    Returns diagnostic status of the RAG system and vector database.
    """
    import chromadb
    chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chroma")
    embed_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    llm_provider = os.getenv("LLM_PROVIDER", "gemini")

    status = {
        "embedding_provider": "Gemini (Cloud)" if llm_provider in ["gemini", "auto"] else "Local / Fallback",
        "embedding_model": embed_model,
        "vector_database": "ChromaDB (Persistent)",
        "chroma_path": chroma_path,
        "collections": [],
        "total_chunks_indexed": 0
    }

    try:
        client = chromadb.PersistentClient(path=chroma_path)
        colls = client.list_collections()
        total_chunks = 0
        coll_list = []
        for c in colls:
            count = c.count()
            total_chunks += count
            coll_list.append({
                "name": c.name,
                "count": count
            })
        status["collections"] = coll_list
        status["total_chunks_indexed"] = total_chunks
    except Exception as e:
        status["error"] = str(e)

    return status


def print_rag_status():
    """
    Prints clean startup banner for RAG status.
    """
    status = get_rag_status()
    print("=" * 60)
    print("ABHYAS AI — RAG STATUS & VECTOR STORE INITIALIZATION")
    print("=" * 60)
    print(f"Embedding Provider: {status['embedding_provider']}")
    print(f"Embedding Model:    {status['embedding_model']}")
    print(f"Vector Database:    {status['vector_database']}")
    print(f"Total Chunks:       {status['total_chunks_indexed']}")
    print("Active Collections:")
    for c in status["collections"]:
        print(f"  • {c['name']} ({c['count']} chunks)")
    print("=" * 60)
