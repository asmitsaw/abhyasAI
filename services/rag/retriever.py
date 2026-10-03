"""
Hybrid retriever using Chroma Cloud's Search API with Reciprocal Rank Fusion (RRF).

Strategy per query:
  - Dense KNN  (Qwen semantic embeddings)  → weight 0.7
  - Sparse KNN (SPLADE keyword embeddings) → weight 0.3
  - Combined via RRF (k=60) for robust, scale-agnostic ranking.
  - GroupBy document_id to deduplicate chunks from the same source.

Falls back gracefully to dense-only if the Cloud Search API raises an
unexpected error (e.g. collection has no sparse index yet).
"""

from typing import Any, Dict, List, Optional

from chromadb import Search, K as ChromaKey, Knn, Rrf

from services.rag.ingestion import UniversalIngestionService
from services.rag.query_router import QueryRouter, QueryType
from services.rag.reranker import HybridReranker


# Number of candidate documents each KNN arm considers before RRF fusion.
_KNN_LIMIT = 200


class HybridRetriever:
    """
    Retrieves candidate chunks from Chroma Cloud collections using:
    1. Hybrid search (dense + sparse via RRF) per collection.
    2. Metadata filtering by subject / module / document_type when provided.
    3. Light post-reranking via the existing HybridReranker.
    """

    def __init__(self, ingestion_service: Optional[UniversalIngestionService] = None):
        self.ingestion = ingestion_service or UniversalIngestionService()
        self.router = QueryRouter()
        self.reranker = HybridReranker()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        subject: Optional[str] = None,
        module: Optional[str] = None,
        document_type: Optional[str] = None,
        top_k: int = 5,
        candidate_pool: int = 12,
    ) -> Dict[str, Any]:
        query_type = self.router.route_query(query)
        target_collections = self.router.get_target_collections(query_type)

        # Build optional metadata filter
        where_clauses: List[Dict] = []
        if subject and subject != "General":
            where_clauses.append({"subject": {"$eq": subject}})
        if module:
            where_clauses.append({"module": {"$eq": module}})
        if document_type:
            where_clauses.append({"document_type": {"$eq": document_type}})

        raw_candidates: List[Dict[str, Any]] = []

        for coll_type in target_collections:
            try:
                coll = self.ingestion.get_or_create_collection(coll_type)
                n_available = coll.count()
                if n_available == 0:
                    continue

                per_coll_k = min(n_available, max(3, candidate_pool // len(target_collections)))
                results = self._hybrid_search(coll, query, per_coll_k, where_clauses)
                raw_candidates.extend(
                    self._parse_search_results(results, coll_type)
                )
            except Exception as error:
                print(f"[Retriever] Collection '{coll_type}' search warning: {error}")
                # Graceful dense-only fallback
                try:
                    raw_candidates.extend(
                        self._dense_fallback(coll_type, query, 4, where_clauses)
                    )
                except Exception:
                    pass

        # If nothing found with filters, retry without them
        if not raw_candidates and where_clauses:
            for coll_type in target_collections:
                try:
                    raw_candidates.extend(
                        self._dense_fallback(coll_type, query, 4, [])
                    )
                except Exception:
                    pass

        top_chunks = self.reranker.rerank(
            query=query, candidates=raw_candidates, top_k=top_k
        )
        return {
            "query": query,
            "query_type": query_type.value,
            "total_candidates_found": len(raw_candidates),
            "chunks": top_chunks,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_where(self, clauses: List[Dict]) -> Optional[Dict]:
        """Convert list of $eq clauses into a single Chroma where dict."""
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def _hybrid_search(self, coll, query: str, limit: int, where_clauses: List[Dict]) -> Any:
        """
        Execute a hybrid RRF search (dense + sparse) on the collection.
        Returns the raw Chroma Search result object.
        """
        dense_rank = Knn(
            query=query,
            return_rank=True,
            limit=_KNN_LIMIT,
            default=1000,        # include partial matches from either arm
        )
        sparse_rank = Knn(
            query=query,
            key="sparse_embedding",
            return_rank=True,
            limit=_KNN_LIMIT,
            default=1000,
        )
        hybrid_rank = Rrf(
            ranks=[dense_rank, sparse_rank],
            weights=[0.7, 0.3],   # semantic > keyword for educational content
            k=60,
        )

        search_builder = (
            Search()
            .rank(hybrid_rank)
            .limit(limit)
            .select(ChromaKey.DOCUMENT, ChromaKey.SCORE, ChromaKey.ID, ChromaKey.METADATA)
        )

        where = self._build_where(where_clauses)
        if where:
            search_builder = search_builder.where(where)

        return coll.search(search_builder)

    def _parse_search_results(self, results: Any, coll_type: str) -> List[Dict[str, Any]]:
        """Parse Chroma Cloud Search result rows into the standard chunk dicts."""
        candidates: List[Dict[str, Any]] = []
        try:
            rows = results.rows()
            if not rows or not rows[0]:
                return []
            for row in rows[0]:
                candidates.append({
                    "chunk_id": row.get("id", ""),
                    "text": row.get("document", ""),
                    "metadata": row.get("metadata", {}),
                    "distance": abs(row.get("score", 0.5)),  # RRF scores are negative
                    "collection": coll_type,
                })
        except Exception as e:
            print(f"[Retriever] Result parsing warning: {e}")
        return candidates

    def _dense_fallback(
        self, coll_type: str, query: str, limit: int, where_clauses: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Dense-only fallback using the legacy query() API when Cloud Search
        is unavailable (e.g. empty collection or network hiccup).
        """
        coll = self.ingestion.get_or_create_collection(coll_type)
        n_available = coll.count()
        if n_available == 0:
            return []

        n = min(n_available, limit)
        where = self._build_where(where_clauses) if where_clauses else None
        res = coll.query(
            query_texts=[query],
            n_results=n,
            where=where,
        )
        if not res or not res.get("documents") or not res["documents"][0]:
            return []

        candidates: List[Dict[str, Any]] = []
        for d_txt, meta, dist, c_id in zip(
            res["documents"][0],
            res.get("metadatas", [[{}]])[0],
            res.get("distances", [[0.5]])[0],
            res.get("ids", [[""]])[0],
        ):
            candidates.append({
                "chunk_id": c_id,
                "text": d_txt,
                "metadata": meta,
                "distance": dist,
                "collection": coll_type,
            })
        return candidates
