# services/rag package — lazy imports to avoid startup errors when CHROMA_API_KEY is not yet set.

def get_rag_pipeline():
    from services.rag.rag_pipeline import get_rag_pipeline as _get
    return _get()

class RAGPipeline:
    def __new__(cls, *args, **kwargs):
        from services.rag.rag_pipeline import RAGPipeline as _RAGPipeline
        return _RAGPipeline(*args, **kwargs)

__all__ = ["RAGPipeline", "get_rag_pipeline"]
