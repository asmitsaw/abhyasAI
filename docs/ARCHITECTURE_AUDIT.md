# AbhyasAI — Complete Architectural Audit & Migration Specification

## 1. Executive Summary

AbhyasAI is currently an AI-powered academic assistance application built on Flask, Google GenAI SDK, Pydantic, and pypdf with a comic-book / neobrutalist aesthetic. While its existing core pipelines (YouTube transcript-to-quiz generation, AI tutor chat, and multi-stage exam blueprinting & paper generation) are functional, the system operates as a stateless content generation tool rather than an intelligent, adaptive learning system.

This audit establishes the baseline of the current codebase, documents all existing routes, services, data structures, and limitations, and presents the target architecture to transform AbhyasAI into an **AI Exam Intelligence and Personalized Learning System**.

---

## 2. Current Architecture & Baseline Inventory

### 2.1 Technology Stack
- **Web Backend**: Flask 3.1.3 (WSGI server in `app.py`)
- **Language Models**: Google Gemini GenAI SDK (`google-genai==2.20.0`), default model `gemini-3.8-flash` with retry/fallback
- **Data Validation & Schemas**: Pydantic v2 (`pydantic==2.13.5`)
- **Document Processing**: `pypdf==6.18.0` for PDF text extraction; standard regex for normalization
- **External Data**: `youtube-transcript-api==1.2.4` for fetching subtitles
- **Frontend**: Jinja2 HTML5 templates, Vanilla CSS (`static/css/style.css`), Vanilla JavaScript
- **Testing**: Standalone scripts using standard assertions and Flask test client

### 2.2 Existing Routes & Controllers

| Route | Method | Controller File | Purpose | Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | GET | `app.py` | Homepage / Landing page | Active |
| `/learn` | GET | `app.py` | YouTube learning & quiz interface | Active |
| `/process-youtube` | POST | `app.py` | Extracts video ID, gets transcript, generates 20 MCQs | Active |
| `/ask-tutor` | POST | `app.py` | Context-grounded tutor doubt clearing | Active |
| `/test-gemini` | GET | `app.py` | Diagnostic Gemini connectivity test | Active |
| `/exam/` | GET | `routes/exam_routes.py` | Exam preparation workspace | Active (Blueprint) |
| `/exam/generate` | POST | `routes/exam_routes.py` | Runs 6-stage exam paper generation pipeline | Active (Blueprint) |
| `/learning/learn` | GET | `routes/learning_routes.py` | Standalone learn page template | Inactive (Unmounted) |
| `/learning/quiz` | GET | `routes/learning_routes.py` | Standalone quiz page template | Inactive (Unmounted) |
| `/learning/tutor` | GET | `routes/learning_routes.py` | Standalone tutor page template | Inactive (Unmounted) |
| `/viva/` | GET | `routes/viva_routes.py` | Standalone viva page template | Inactive (Unmounted) |
| `/viva/result` | GET | `routes/viva_routes.py` | Standalone viva results template | Inactive (Unmounted) |

### 2.3 Existing Services

| Service File | Role | Implementation Status |
| :--- | :--- | :--- |
| `services/gemini_service.py` | Gemini client with retry, backoff, and fallback models | Operational |
| `services/document_service.py` | File text extraction (PDF, TXT, MD) and cleaning | Operational |
| `services/syllabus_service.py` | Structured syllabus extraction into `Syllabus` model | Operational |
| `services/pyq_analysis_service.py` | PYQ mapping, module weightages, recurring patterns | Operational |
| `services/exam_blueprint_service.py` | Exam blueprint generation with question specifications | Operational |
| `services/paper_generation_service.py`| Practice Paper 1 (Set A) and Paper 2 (Set B) generation | Operational |
| `services/validation_service.py` | Rule-based verification of marks and question overlap | Operational |
| `services/exam_prep_pipeline.py` | End-to-end coordinator for exam preparation | Operational |
| `services/youtube_service.py` | YouTube URL parsing (standard, short, shorts) | Operational |
| `services/transcript_service.py` | YouTube subtitle retrieval via `youtube-transcript-api`| Operational |
| `services/quiz_service.py` | 20-question MCQ generator with JSON schema validation | Operational |
| `services/tutor_service.py` | AI Tutor doubt-solver grounded in lecture transcript | Operational |
| `services/evaluation_service.py` | Free-text response evaluation and rubric grading | Stub (Empty) |
| `services/paper_generator.py` | Redundant / legacy paper generator stub | Stub (Empty) |
| `services/pyq_service.py` | Standalone PYQ indexing stub | Stub (Empty) |
| `services/viva_service.py` | Oral examination / Viva Voce session management | Stub (Empty) |

### 2.4 Data Models & Persistence Audit

- **Pydantic Schemas (`models/exam_models.py`)**: Well-structured schemas for `SyllabusModule`, `Syllabus`, `PYQQuestionAnalysis`, `PYQAnalysis`, `BlueprintQuestionSpec`, `ExamBlueprint`, `ExamQuestion`, `ExamSection`, `PracticePaper`, `PracticePaperSet`.
- **Placeholder Models**: `models/question.py`, `models/quiz.py`, and `models/user.py` are empty 1-line stubs.
- **In-Memory Volatility**:
  - `TRANSCRIPT_STORE = {}` in `app.py`: All lecture transcripts are stored in a process-level Python dictionary. Server restarts wipe all student session data.
  - Generated exam papers are returned as pure JSON over HTTP to the browser DOM; neither raw files nor structured records are persisted to `data/generated_papers/` or any database.
- **Database**: There is currently **zero persistent database storage** (no SQLite, no SQLAlchemy, no migrations).

---

## 3. Current Limitations & Fragile Assumptions

1. **No RAG Infrastructure**:
   - Transcripts and past papers are injected directly and in their entirety into single LLM prompts.
   - For long syllabi or multi-year PYQs, this risks prompt truncation, high token cost, and hallucinated coverage.
   - There is no semantic vector store (ChromaDB), no structure-aware chunking, and no citation engine.
2. **Stateless Student Learning**:
   - The system has no concept of a student identity, subject enrollment, topic mastery, or historical quiz attempts.
   - It cannot answer: *"What is my weakest topic?"* or *"What should I study next?"*
3. **Hardcoded Model Coupling**:
   - `services/gemini_service.py` hardcodes `gemini-3.8-flash` and `gemini-3.6-flash`. There is no abstraction to switch providers or support local inference (e.g. Ollama/vLLM with Qwen).
4. **Non-Adaptive Assessment**:
   - Quizzes are static one-shot batches of 20 questions generated all at once; question difficulty does not adapt dynamically based on previous answer correctness.
5. **Incomplete Scaffolding**:
   - The Viva Voce mode is solely static HTML without an active state machine, voice synthesis/transcription, or adaptive follow-up questioning.
   - The Exam mode displays paper text but lacks an interactive exam simulation environment (timer, autosave, mark for review, question palette, scoring).

---

## 4. Proposed Target Architecture

```
                       STUDENT / CLIENT
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       Neobrutalist UI              REST API Layer
   (Dashboard, Exam, Viva,        (Flask Blueprints)
    RAG Tutor, Adaptive Quiz)                │
               │                             │
               ▼                             ▼
     ┌──────────────────────────────────────────────────┐
     │            CORE INTELLIGENCE LAYER               │
     │  - Student Mastery Engine (Deterministic 0-100)  │
     │  - Study Planner & "What Should I Study Now?"    │
     │  - PYQ Historical Relevance & Evidence Engine    │
     │  - Adaptive Diagnostic & Practice Engine         │
     │  - Answer Evaluator & Exam Answer Mode           │
     │  - Interactive Viva Voce Engine                  │
     │  - Knowledge & Concept Graph                     │
     └──────────────┬───────────────────┬───────────────┘
                    │                   │
                    ▼                   ▼
     ┌───────────────────────┐  ┌───────────────────────┐
     │   LLM PROVIDER LAYER  │  │     RAG SUBSYSTEM     │
     │  - BaseProvider       │  │  - Universal Ingestion │
     │  - GeminiProvider     │  │  - Structure Chunking  │
     │  - LocalProvider      │  │  - ChromaDB Vector DB  │
     │  - ProviderFactory    │  │  - Hybrid Retrieval    │
     │  (gemini/local/auto)  │  │  - Citation Builder    │
     └───────────────────────┘  └───────────────────────┘
                    │                   │
                    ▼                   ▼
     ┌──────────────────────────────────────────────────┐
     │              PERSISTENCE SUBSYSTEM               │
     │   SQLAlchemy (SQLite `abhyas.db` / PostgreSQL)   │
     │   Users, Subjects, Exams, TopicMastery, Attempts │
     │   ChromaDB Persistent Store (`data/chroma/`)     │
     └──────────────────────────────────────────────────┘
```

---

## 5. Phased Incremental Migration Plan

To maintain 100% backward compatibility and prevent regression of existing operational features, the implementation proceeds sequentially:

### Phase 1: LLM Provider Abstraction
- Create `services/llm/` with `base_provider.py`, `gemini_provider.py`, `local_provider.py`, and `provider_factory.py`.
- Support `LLM_PROVIDER=gemini|local|auto` and fallback to Gemini if local is unavailable.
- Retain existing `services/gemini_service.py` API signatures as lightweight delegations to the provider factory.

### Phase 2: RAG Infrastructure & ChromaDB Ingestion
- Create `services/rag/` modules: `metadata.py`, `chunking.py`, `embeddings.py`, `ingestion.py`, `retriever.py`, `reranker.py`, `query_router.py`, `context_builder.py`, `citation_builder.py`, `evaluation.py`, and `rag_pipeline.py`.
- Configure persistent ChromaDB in `data/chroma/`.
- Implement universal ingestion for PDF, TXT, MD, DOCX, PPTX, YouTube transcripts, and pasted notes with SHA-256 deduplication and structure-aware chunking.

### Phase 3: Persistent Student State & Database Models
- Configure SQLAlchemy with SQLite default (`abhyas.db`).
- Implement relational models: `User`, `Subject`, `Exam`, `StudentSubject`, `StudentTopicMastery`, `QuizAttempt`, `QuestionAttempt`, `ExamAttempt`, `VivaAttempt`, `StudySession`, `StudyPlan`, `LearningEvent`.

### Phase 4: Mastery Engine & PYQ Relevance Intelligence
- Implement `services/mastery_service.py` with an interpretable, deterministic 0–100 scoring algorithm (Critical, Weak, Developing, Strong, Mastered).
- Build historical PYQ relevance analytics (frequency, recency, marks coverage, evidence traces).
- Expose `/api/mastery/<subject>` and `/api/evidence/<topic>`.

### Phase 5: "What Should I Study Now?" & Study Planner
- Implement `services/study_planner_service.py` generating time-constrained, prioritized study schedules.
- Add the primary dashboard action card: **"WHAT SHOULD I STUDY NOW?"** with evidence justification and one-click session start.
- Add the **"I'M COOKED 🚨"** emergency cramming engine.

### Phase 6: Adaptive Assessment & Answer Evaluation
- Implement `services/adaptive_quiz_service.py` for dynamic difficulty adjustment and weak-topic reinforcement.
- Implement `services/answer_evaluator.py` supporting 2, 5, 10, and 15-mark rubric evaluations grounded in syllabus/PYQ context.

### Phase 7: Viva Voce & Timed Exam Simulator
- Implement `services/viva_service.py` state machine with examiner personas (Professor, Strict Examiner, Friendly Mentor) and adaptive follow-up questioning.
- Implement interactive timed exam simulator with autosave, question navigation palette, review marking, and post-exam readiness reports.

### Phase 8: Unified Dashboard, Knowledge Graph UI & Demo Mode
- Build primary dashboard featuring Overall Readiness, Topic Mastery heatmaps, Concept Graph, and Study Action cards.
- Implement `DEMO_MODE=true` with pre-seeded Operating Systems curriculum, past papers, and student performance data for reliable hackathon presentation.
- Create automated test suite in `tests/` and update system documentation.
