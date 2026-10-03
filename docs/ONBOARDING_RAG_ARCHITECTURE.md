# AbhyasAI Onboarding & Hybrid RAG Architecture

## 1. System Overview

AbhyasAI combines:
- **Supabase**: Relational entity storage, GoTrue JWT authentication, and persistent chat transcripts.
- **Chroma Cloud**: Scalable vector repository with dense Qwen3 (1024-dim) and sparse SPLADE keyword embeddings, queried via Reciprocal Rank Fusion (RRF).
- **Google Gemini**: Academic reasoning engine executing over grounded, structured chunk evidence.
- **Flask**: Application routing, validation, tenant scoping, and session lifecycle management.

```
                    ┌─────────────────────────┐
                    │     Supabase / Auth     │
                    │                         │
                    │ • User Identity (GoTrue)│
                    │ • Study Sessions        │
                    │ • Documents Metadata    │
                    │ • Persistent Chat State │
                    │ • Row Level Security    │
                    └───────────┬─────────────┘
                                │
                                │
[ STUDENT USER ]                │
       │                        │
       ▼                        │
   /login ──────────────────────┘
       │ (Session / Bearer Token)
       ▼
  /onboarding 
       │
       ├── Subject / Session Name
       │
       └── Multi-File Upload (Up to 3 Files)
                │
                ▼
      SERVICES/INGESTION/MANAGER
                │
     ┌──────────┼───────────────┬────────────────┐
     ▼          ▼               ▼                ▼
 PDF PARSER  DOCX PARSER   PPTX PARSER   IMAGE / XLSX / TEXT
     │          │               │                │
     └──────────┴───────┬───────┴────────────────┘
                        │
                        ▼
             NormalizedDocument
                        │
                        ▼
             StructureAwareChunker
                        │
                        ▼
             Chroma Vector Ingestion
                        │
            ┌───────────┴───────────┐
            │     CHROMA CLOUD      │
            │                       │
            │ • Dense (Qwen 1024)   │
            │ • Sparse (SPLADE)     │
            │ • user_id + session_id│
            └───────────┬───────────┘
                        │
                        ▼
                 [ SESSION READY ]
                        │
                        ▼
                   /dashboard
                        │
                        ▼
       Interactive Study Space Chatbot
```

---

## 2. Multi-Tenant Isolation Guarantee

Multi-tenancy is enforced at three non-bypassable layers:

1. **Authentication & Identity Layer**:
   - The backend extracts `user_id` strictly from verified Supabase GoTrue tokens (`Bearer <jwt>`) or server sessions.
   - Frontend-supplied `user_id` values are never trusted or consulted.
2. **Relational Data Layer**:
   - Every study session, document, chat session, and message in Supabase is keyed to `user_id`.
   - PostgREST Row Level Security (RLS) ensures `user_id = auth.uid()`.
   - API endpoints reject foreign session requests with `404 Not Found`.
3. **Vector Retrieval Layer**:
   - In [services/rag/retriever.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/retriever.py), `where_clauses` must include:
     ```python
     where_clauses = [
         {"user_id": {"$eq": str(user_id)}},
         {"session_id": {"$eq": str(session_id)}}
     ]
     ```
   - Even when topic or module search filters are relaxed to improve recall, tenant filters (`user_id` and `session_id`) are never relaxed.

---

## 3. Grounded Retrieval Flow

When a user submits a question in the dashboard:

```
[ Question: "What is deadlock prevention?" ]
                 ↓
[ 1. Auth & Session Validation ]
     Verifies user owns selected session
                 ↓
[ 2. User Message Saved ]
     Appended to chat_messages table
                 ↓
[ 3. Query Routing ]
     QueryRouter assigns query category
                 ↓
[ 4. Chroma Cloud Hybrid Search ]
     Dense Qwen KNN (weight 0.7) + Sparse SPLADE KNN (weight 0.3)
     Filtered strictly by user_id and session_id
                 ↓
[ 5. Reciprocal Rank Fusion (RRF) ]
     RRF scoring (k=60) merges ranking lists
                 ↓
[ 6. Hybrid Reranking ]
     Relevance scored against target topic
                 ↓
[ 7. Context Builder & Injection Defense ]
     Prepend UNTRUSTED REFERENCE MATERIAL security banner
                 ↓
[ 8. Gemini Generation ]
     Grounded answer with inline citation tags [1], [2]
                 ↓
[ 9. Assistant Message Saved ]
     Answer + JSON citations persisted to Supabase
                 ↓
[ 10. Dashboard Stream ]
     Formatted answer with interactive clickable citations
```
