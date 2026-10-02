from typing import Any, Dict, List, Optional
from services.rag.ingestion import UniversalIngestionService
from services.rag.query_router import QueryRouter, QueryType
from services.rag.reranker import HybridReranker


class HybridRetriever:
    """
    Retrieves candidate chunks across ChromaDB collections with metadata filtering,
    semantic vector query, and hybrid reranking.
    """

    def __init__(self, ingestion_service: Optional[UniversalIngestionService] = None):
        self.ingestion = ingestion_service or UniversalIngestionService()
        self.router = QueryRouter()
        self.reranker = HybridReranker()

    def retrieve(
        self,
        query: str,
        subject: Optional[str] = None,
        module: Optional[str] = None,
        document_type: Optional[str] = None,
        top_k: int = 5,
        candidate_pool: int = 12
    ) -> Dict[str, Any]:
        query_type = self.router.route_query(query)
        target_collections = self.router.get_target_collections(query_type)

        where_filter: Dict[str, Any] = {}
        if subject and subject != "General":
            where_filter["subject"] = subject
        if module:
            where_filter["module"] = module
        if document_type:
            where_filter["document_type"] = document_type

        filter_arg = where_filter if where_filter else None

        raw_candidates: List[Dict[str, Any]] = []

        for coll_type in target_collections:
            try:
                coll = self.ingestion.get_or_create_collection(coll_type)
                n_available = coll.count()
                if n_available == 0:
                    continue

                per_coll_k = min(n_available, max(3, candidate_pool // len(target_collections)))
                res = coll.query(
                    query_texts=[query],
                    n_results=per_coll_k,
                    where=filter_arg
                )

                if res and "documents" in res and res["documents"] and res["documents"][0]:
                    docs = res["documents"][0]
                    metas = res["metadatas"][0] if "metadatas" in res and res["metadatas"] else [{}] * len(docs)
                    dists = res["distances"][0] if "distances" in res and res["distances"] else [0.5] * len(docs)
                    ids = res["ids"][0] if "ids" in res and res["ids"] else [""] * len(docs)

                    for d_txt, m, dist, c_id in zip(docs, metas, dists, ids):
                        raw_candidates.append({
                            "chunk_id": c_id,
                            "text": d_txt,
                            "metadata": m,
                            "distance": dist,
                            "collection": coll_type
                        })
            except Exception as error:
                print(f"[Retriever] Collection {coll_type} search warning: {error}")

        # If nothing found with strict filter, retry without metadata filter
        if not raw_candidates and filter_arg:
            for coll_type in target_collections:
                try:
                    coll = self.ingestion.get_or_create_collection(coll_type)
                    if coll.count() == 0:
                        continue
                    res = coll.query(query_texts=[query], n_results=min(coll.count(), 4))
                    if res and "documents" in res and res["documents"] and res["documents"][0]:
                        for d_txt, m, dist, c_id in zip(
                            res["documents"][0],
                            res["metadatas"][0],
                            res["distances"][0],
                            res["ids"][0]
                        ):
                            raw_candidates.append({
                                "chunk_id": c_id,
                                "text": d_txt,
                                "metadata": m,
                                "distance": dist,
                                "collection": coll_type
                            })
                except Exception:
                    pass

        # Rerank and select top_k
        top_chunks = self.reranker.rerank(query=query, candidates=raw_candidates, top_k=top_k)

        return {
            "query": query,
            "query_type": query_type.value,
            "total_candidates_found": len(raw_candidates),
            "chunks": top_chunks
        }
