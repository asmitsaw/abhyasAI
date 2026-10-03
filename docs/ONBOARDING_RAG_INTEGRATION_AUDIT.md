# AbhyasAI — Onboarding, RAG, Supabase & Chat Integration Audit

**Date**: 2026-10-03  
**Status**: Completed Pre-Implementation Audit  
**Author**: Antigravity Pair Programmer  

---

## 1. Existing Onboarding Implementation

### Current Location & Structure
- **Template**: [templates/onboarding.html](file:///c:/Users/asmit/Downloads/AbhyasAI/templates/onboarding.html)
- **Controller Route**: `/onboarding` in [app.py](file:///c:/Users/asmit/Downloads/AbhyasAI/app.py#L92-L95)
- **Processing Endpoint**: `POST /api/process-materials` in [routes/api_routes.py](file:///c:/Users/asmit/Downloads/AbhyasAI/routes/api_routes.py#L413-L594)

### Current Behavior
- Hardcoded inputs for 4 specific slots:
  1. `subject` (text input, default "Operating Systems")
  2. `syllabus_file` or `syllabus_text`
  3. `pyq1`, `pyq2`, `pyq3` (individual file inputs for past year papers)
  4. `notes_file` (optional notes)
- Uses client-side simulation for 7 timeline steps with artificial delays (`delay(120)`).
- Submits to `/api/process-materials` which attempts text extraction, PYQ parsing, and basic indexing.
- Stores current subject in Flask session (`session["current_subject"] = subject_name`) and student in SQLite (`User(id=student_id)`).

### Limitations Against New Spec
- The page is structured specifically around the old 4-slot model rather than a flexible **Study Session** concept.
- Lacks modern multi-file drag-and-drop card UI with `0/3`, `1/3`, `2/3`, `3/3` file counters.
- Does not enforce the 3-file session limit cleanly.
- Does not handle broad document formats (.docx, .pptx, .csv, .xlsx, images with OCR/multimodal extraction).
- Displays fake progress timers rather than reflecting granular backend indexing state.

---

## 2. Existing Login / Auth Implementation

### Current Status
- **Authentication**: **None**. Currently completely unauthenticated.
- **Identity Mechanism**: Uses `session.get("student_id", 1)` fallback (`def get_current_student_id() -> int` in [routes/api_routes.py](file:///c:/Users/asmit/Downloads/AbhyasAI/routes/api_routes.py#L33-L35)).
- **Templates**: No `login.html` or `signup.html` exists in `templates/`.
- **Security Vulnerability**: Frontend can manipulate or act as any user without token verification or session authentication.

### Requirements to Meet Spec
- Integrate Supabase Auth (`/login` template with sign-up, sign-in, session storage, token verification).
- Add session/token validation on backend: derive `authenticated_user.id` from verified Supabase JWT / session cookie.
- Protect routes: `/dashboard`, `/onboarding`, `/api/chat`, `/api/study-sessions`, `/api/documents`, `/api/rag/query`. Return `401 Unauthorized` for APIs or redirect to `/login` for page views when unauthenticated.

---

## 3. Existing Database

### Current Status
- **ORM / Engine**: SQLAlchemy declarative base in [models/database.py](file:///c:/Users/asmit/Downloads/AbhyasAI/models/database.py).
- **Default Connection**: `sqlite:///abhyas.db` configured via `DATABASE_URL` in [config/config.py](file:///c:/Users/asmit/Downloads/AbhyasAI/config/config.py) and [.env.example](file:///c:/Users/asmit/Downloads/AbhyasAI/.env.example#L37).
- **Existing Entities**:
  - `User` (id, username, email, created_at)
  - `Subject` (id, name, code, syllabus_json, created_at)
  - `Exam`
  - `StudentSubject`
  - `StudentTopicMastery` (topic_name, mastery_score, confidence, attempt_count, correct_count)
  - `QuizAttempt` & `QuestionAttempt`
  - `ExamAttempt`
  - `VivaAttempt`
  - `StudySession` (student_id, subject_id, topic_name, duration_minutes, completed, session_type)
  - `StudyPlan`
  - `LearningEvent`
- **Missing Entities**:
  - `Document` model (document_id, session_id, user_id, filename, file_size, mime_type, chunk_count, status).
  - `ChatSession` & `ChatMessage` models for persistent RAG conversation history.

---

## 4. Existing Supabase Integration

### Current Status
- **Supabase in Code**: **Zero** prior references in repository.
- **Environment**: `.env.example` does not yet declare `SUPABASE_URL`, `SUPABASE_ANON_KEY`, or `SUPABASE_SERVICE_ROLE_KEY`.

### Integration Strategy
- Add Supabase credentials to `.env.example` and load them in `config/config.py`.
- Create `services/supabase_service.py` to handle:
  - Supabase Auth (token verification, user info).
  - Supabase Database / PostgREST (study sessions, documents, chat conversations, chat messages).
  - Graceful fallback / sync to local SQLite so offline development and tests never break when keys are absent.
- Provide SQL migration with Row Level Security (RLS) policies in `migrations/20261003_supabase_auth_sessions_chat.sql`.

---

## 5. Existing Chroma Cloud Integration

### Current Status
- **Client**: [services/rag/embeddings.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/embeddings.py) uses `chromadb.CloudClient` with:
  - `tenant = os.environ.get("CHROMA_TENANT", "688bc2df-d727-4a69-9f2e-5fa46471ce1c")`
  - `database = os.environ.get("CHROMA_DATABASE", "abhyasAI")`
  - `api_key = os.environ.get("CHROMA_API_KEY")`
- **Embeddings**:
  - Dense: `ChromaCloudQwenEmbeddingFunction` (Qwen3 0.6B, 1024 dims).
  - Sparse: `ChromaCloudSpladeEmbeddingFunction` (SPLADE keyword weights).
  - Hybrid Index: `get_hybrid_schema()` builds `Schema` containing both dense VectorIndexConfig and sparse SparseVectorIndexConfig.
- **Collections**: Type-sharded (e.g., `abhyas_notes`, `abhyas_documents`, `abhyas_syllabus`, `abhyas_pyq`).

### Changes Required for Session Isolation
- Currently collections are sharded by document type, but chunks do not consistently require `user_id` and `session_id` in `ChunkMetadata`.
- Must include `user_id` and `session_id` in chunk metadata and enforce `where={"$and": [{"user_id": {"$eq": user_id}}, {"session_id": {"$eq": session_id}}]}` in `HybridRetriever`.

---

## 6. Existing Ingestion Pipeline

### Current Status
- **Service**: [services/rag/ingestion.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/ingestion.py) (`UniversalIngestionService`).
- **Chunker**: [services/rag/chunking.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/chunking.py) (`StructureAwareChunker`).
- **File Parsing**:
  - PDF: [services/document_service.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/document_service.py) via `pypdf.PdfReader`.
  - DOCX: `_extract_docx` using `python-docx`.
  - PPTX: `_extract_pptx` using `python-pptx`.
  - TXT / MD: Plaintext decoding.
  - Images / Spreadsheets: Missing or partial.

### Extensions Required
- Refactor/extend ingestion into modular parsers:
  - PDF parser (`pypdf` with page-aware extraction).
  - DOCX parser (`python-docx` with paragraph/section tracking).
  - PPTX parser (`python-pptx` with slide number and title tracking).
  - Spreadsheet parser (CSV, XLSX via `openpyxl` with sheet names and table rows).
  - Text parser (TXT, MD, RTF with encoding detection and sanitization).
  - Image parser (PNG, JPG, JPEG, WEBP with vision extraction via Gemini multimodal provider, falling back to OCR).
- Retain existing `UniversalIngestionService` interface for full backward compatibility.

---

## 7. Existing RAG Pipeline

### Current Status
- **Pipeline Coordinator**: [services/rag/rag_pipeline.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/rag_pipeline.py) (`RAGPipeline`).
- **Retriever**: [services/rag/retriever.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/retriever.py) (`HybridRetriever` with RRF fusion of dense Qwen and sparse SPLADE).
- **Reranker**: [services/rag/reranker.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/reranker.py) (`HybridReranker`).
- **Citations**: [services/rag/citation_builder.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/citation_builder.py) (`CitationBuilder`).
- **Context**: [services/rag/context_builder.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/rag/context_builder.py) (`ContextBuilder`).
- **Synthesis**: [services/llm/provider_factory.py](file:///c:/Users/asmit/Downloads/AbhyasAI/services/llm/provider_factory.py) -> `GeminiProvider`.

### Extensions Required
- Parameterize `retriever.retrieve(...)` and `rag_pipeline.query(...)` with `user_id` and `session_id`.
- Add prompt injection defense instruction to `ContextBuilder`: explicitly instruct model that retrieved content is untrusted source data and cannot override system instructions.
- Ensure citations include snippet text and sheet/slide metadata so source viewer can render them.

---

## 8. Existing Dashboard Chat

### Current Status
- **Dashboard**: [templates/dashboard.html](file:///c:/Users/asmit/Downloads/AbhyasAI/templates/dashboard.html).
- **Current Content**: Contains mastery metrics, "What Should I Study Now" banner, PYQ intelligence table, Knowledge Graph visualization, and quick actions.
- **Chat UI on Dashboard**: **Currently absent**. (YouTube chat exists in `learn.html`, but dashboard has no embedded study session chatbot).

### Extensions Required
- Integrate a sleek, collapsible or docked Neobrutalist AI Chatbot into `dashboard.html`.
- Session selector dropdown (`Current Study Space: [ Operating Systems ▼ ]`).
- Real-time conversation stream, grounded answers with interactive citation pills `[1]`, source viewer modal, and conversation history sidebar.

---

## 9. Existing Chat / History Implementation

### Current Status
- **Persistence**: No persistent chat history exists. Only `TRANSCRIPT_STORE` (an in-memory dictionary for YouTube transcripts) exists in `app.py`.
- **Database Schema**: No `chat_sessions` or `chat_messages` tables exist in SQLite or Supabase.

### Target Schema
- `chat_sessions`: `id`, `user_id`, `study_session_id`, `title`, `created_at`, `updated_at`.
- `chat_messages`: `id`, `chat_session_id`, `user_id`, `role`, `content`, `citations_json`, `created_at`.
- Handled through `services/supabase_service.py` with RLS.

---

## 10. Files That Must Be Modified

1. **`app.py`**:
   - Register auth middleware / decorators (`@login_required`).
   - Add `/login`, `/logout` page routes.
   - Update `/onboarding` and `/dashboard` to pass auth context.
2. **`config/config.py`**:
   - Add Supabase settings (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `MAX_FILE_SIZE_MB`).
3. **`.env.example`**:
   - Document new Supabase and ingestion configuration variables.
4. **`models/database.py`**:
   - Add `StudySpace`, `DocumentRecord`, `ChatSessionRecord`, `ChatMessageRecord` to SQLite fallback models.
5. **`services/rag/metadata.py`**:
   - Extend `ChunkMetadata` to store `user_id`, `session_id`, `slide`, `sheet`, `snippet`.
6. **`services/rag/retriever.py`**:
   - Add `user_id` and `session_id` scoping to `_hybrid_search` and `_dense_fallback` queries. Never strip tenant filters.
7. **`services/rag/rag_pipeline.py`**:
   - Support `user_id` and `session_id` in `query()`.
8. **`services/rag/context_builder.py`**:
   - Add explicit prompt injection defense instructions.
9. **`services/rag/citation_builder.py`**:
   - Capture chunk snippet and slide/sheet metadata for citation popup.
10. **`services/rag/ingestion.py`**:
    - Extend with modular parser dispatch for PDF, DOCX, PPTX, XLSX/CSV, TXT/MD, Image vision.
11. **`templates/onboarding.html`**:
    - Complete redesign per requirements: 0-3 file counter, drag-and-drop, cards, format validation, real progress timeline.
12. **`templates/dashboard.html`**:
    - Add embedded RAG chatbot, study session selector, chat history sidebar, and citation source viewer modal.
13. **`routes/api_routes.py`**:
    - Add/extend session-aware endpoints: study sessions, multi-file upload, chat query with persistence, chat history list/detail.

---

## 11. Files That Should NOT Be Modified

- `services/mastery_service.py` (Core mastery scoring engine)
- `services/study_planner_service.py` (Study plan generation)
- `services/adaptive_quiz_service.py` (Adaptive assessment engine)
- `services/viva_service.py` (Viva voce simulator)
- `services/answer_evaluator.py` (Answer evaluation engine)
- `services/pyq_service.py` & `services/pyq_analysis_service.py` (PYQ analytics)
- `services/exam_simulator_service.py` & `services/exam_prep_pipeline.py` (Exam generation)
- `templates/answer_evaluator.html`, `templates/answer_mode.html`, `templates/viva_arena.html`, `templates/learning/learn.html`
- `static/css/style.css` (Preserve core brand styling, extend where needed)

---

## 12. Potential Merge-Conflict Files

- `app.py`: Central routing hub; must only append routes and auth hooks cleanly.
- `routes/api_routes.py`: Contains existing RAG and assessment endpoints; must extend without breaking `/api/process-materials` or `/api/rag/query`.
- `services/rag/embeddings.py`: Keep `AbhyasEmbeddingFunction` backward compatibility alias intact.
- `models/database.py`: Only append new entity classes without removing existing ones.

---

## 13. Existing Tests That Must Remain Passing

1. **`tests/test_all_subsystems.py`** (13 tests):
   - `test_db_initialization_and_user_creation`
   - `test_mastery_service_baseline_and_update`
   - `test_study_planner_recommendation`
   - `test_study_planner_im_cooked_plan`
   - `test_adaptive_quiz_lifecycle`
   - `test_answer_evaluator_evaluate`
   - `test_answer_evaluator_exemplar`
   - `test_viva_service_lifecycle`
   - `test_exam_simulator_lifecycle`
   - `test_knowledge_graph_service`
   - `test_pyq_service_indexing_and_evidence`
   - `test_demo_service_seeding`
   - `test_learning_events_recording`
2. **`tests/test_real_integration.py`** (22 tests):
   - Page view routes (`/`, `/dashboard`, `/onboarding`, `/answer-evaluator`, `/answer-mode`, `/viva-arena`, `/learn`)
   - API endpoints (`/api/mastery`, `/api/what-to-study-now`, `/api/study-plan`, `/api/evidence`, `/api/answer/evaluate`, `/api/quiz/start`, `/api/viva/start`, `/api/graph`, `/api/dashboard`, `/api/demo/seed`, `/api/process-materials`, `/api/rag/query`, `/api/exam/start`)
3. **`tests/test_rag.py`** (9 tests):
   - `test_chunk_metadata_schema`
   - `test_structure_aware_chunking_syllabus`
   - `test_structure_aware_chunking_pyq`
   - `test_embeddings_deterministic_fallback`
   - `test_query_router_classification`
   - `test_citation_builder`
   - `test_context_builder`
   - `test_hybrid_reranker`
   - `test_universal_ingestion_and_deduplication`
