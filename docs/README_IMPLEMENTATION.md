# AbhyasAI — Implementation Reference & Engineering Manual

## 1. System Architecture Overview

AbhyasAI transforms from a content generator into an **AI Exam Intelligence & Personalized Learning System**. It forms a closed feedback loop:

```
SOURCE MATERIAL (Syllabus, PYQs, Notes, Lectures)
       │
       ▼
UNIVERSAL RAG INGESTION (Structure-Aware Chunking, Deduplication, ChromaDB)
       │
       ▼
SYLLABUS & PYQ HISTORICAL INTELLIGENCE (Weightages, Frequency, Recency, Bloom's Taxonomy)
       │
       ▼
CONCEPT / KNOWLEDGE GRAPH (Curriculum Topology & Prerequisite Mapping)
       │
       ▼
STUDENT KNOWLEDGE STATE & MASTERY ESTIMATION (Deterministic 0-100 Calculation)
       │
       ▼
PERSONALIZED STUDY PLAN & "WHAT SHOULD I STUDY NOW?" / "I'M COOKED 🚨"
       │
       ▼
ADAPTIVE TESTING / MOCK EXAM / AI VIVA VOCE
       │
       ▼
RUBRIC-GROUNDED EVALUATION & MASTERY RE-ESTIMATION
```

---

## 2. LLM Provider Abstraction (`services/llm/`)

- `base_provider.py`: Defines the `LLMProvider` abstract interface:
  - `generate(prompt, system_instruction, temperature, max_tokens, use_reasoning)`
  - `generate_json(prompt, schema, system_instruction, temperature, use_reasoning)`
  - `embed(texts, model)`
  - `health_check()`
- `gemini_provider.py`: Native Google GenAI SDK integration with exponential backoff on HTTP 429 and 503, model fallbacks (`gemini-3.8-flash` -> `gemini-3.6-flash` -> `gemini-flash-latest`), and JSON schema validation.
- `local_provider.py`: OpenAI-compatible client for Ollama or vLLM running models like `Qwen/Qwen3-8B`. Fails gracefully or delegates to cloud provider.
- `provider_factory.py`: Instantiates providers based on `LLM_PROVIDER` (`gemini`, `local`, `auto`). With `auto`, delegates to `AutoFallbackProvider` so the system **never crashes** if local inference is offline.

---

## 3. Modular RAG Pipeline (`services/rag/`)

### 3.1 Universal Ingestion
- Supports **PDF**, **TXT**, **Markdown**, **DOCX**, **PPTX**, **YouTube Transcripts**, and **Pasted Text**.
- Prevents redundant vector storage using SHA-256 document hashing.
- Persistent ChromaDB storage located at `data/chroma/`.

### 3.2 Structure-Aware Chunking
- **Syllabus**: Chunked by Module -> Topic -> Subtopics.
- **PYQ**: Chunked by Year -> Section -> Question Number with marks extraction.
- **Lectures**: Chunked into sequential timestamp segments.
- **Notes**: Chunked by Markdown headers (`#`, `##`, `###`) and page breaks.
- Default configuration: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=120`.

### 3.3 Chroma Collections
- `abhyas_documents_gemini_embedding_001_v1`
- `abhyas_syllabus_gemini_embedding_001_v1`
- `abhyas_pyqs_gemini_embedding_001_v1`
- `abhyas_lectures_gemini_embedding_001_v1`
- `abhyas_notes_gemini_embedding_001_v1`
- `abhyas_questions_gemini_embedding_001_v1`
- `abhyas_concepts_gemini_embedding_001_v1`
- `abhyas_answers_gemini_embedding_001_v1`

### 3.4 Hybrid Retrieval & Grounded Citations
- `query_router.py`: Classifies incoming student prompts into 11 semantic intents:
  - `GENERAL_TUTOR`, `SYLLABUS`, `PYQ`, `EXAM_PATTERN`, `TOPIC`, `LECTURE`, `ANSWER_EVALUATION`, `VIVA`, `STUDY_PLAN`, `CONCEPT`, `REVISION`.
- `reranker.py`: Combines vector cosine similarity, term frequency overlap, exact phrase matches, and metadata alignment.
- `citation_builder.py`: Generates numbered bracket citations `[1]`, `[2]` showing source document, year, question number, and page.
- Strict anti-hallucination guard: Displays *"I couldn't find enough evidence in the uploaded material"* when facts are missing.

---

## 4. Persistent Database Models (`models/database.py`)

Using SQLAlchemy with SQLite default (`abhyas.db`):
- `User`: Student credentials and profiles.
- `Subject`: Course names, codes, and raw syllabus JSON.
- `Exam`: Scheduled exams with target dates and cutoffs.
- `StudentSubject`: Enrolled courses and target grades.
- `StudentTopicMastery`: Stores `mastery_score` (0-100), `confidence` (0-1), `attempt_count`, `correct_count`, `last_attempt`, `last_correct`, `average_response_time`, and `difficulty_seen`.
- `QuizAttempt` & `QuestionAttempt`: Individual quiz logs with question-level timing and correctness.
- `ExamAttempt`: Timed mock exam simulation scores and topic breakdowns.
- `VivaAttempt`: Oral examination records with examiner comments and dialog transcripts.
- `StudySession`: Completed study intervals.
- `StudyPlan`: Active generated study schedules.
- `LearningEvent`: Comprehensive audit log of all interaction events.

---

## 5. Core Intelligence Engines

### 5.1 Mastery Engine (`services/mastery_service.py`)
- **Deterministic 0–100 Calculation**:
  - Accuracy: up to 60 points (`(correct / attempts) * 60`).
  - Difficulty Bonus: up to 20 points (Easy=0.8x, Medium=1.0x, Hard=1.25x).
  - Volume Confidence: up to 15 points (`attempts^0.5 * 4 * accuracy`).
  - Response Time Efficiency: up to 5 points (for 5s–30s responses).
- **Mastery Bands**:
  - `0–39`: **Critical** (Red `#ed2929`)
  - `40–59`: **Weak** (Orange `#ff9800`)
  - `60–74`: **Developing** (Yellow `#ffd91a`)
  - `75–89`: **Strong** (Green `#4caf50`)
  - `90–100`: **Mastered** (Hero Blue `#1595df`)

### 5.2 Historical PYQ Relevance (`services/pyq_service.py`)
- Calculates empirical **Historical Relevance Score** (0–100) based on:
  - `Frequency Weight` (up to 35 pts)
  - `Marks Weight` (up to 35 pts)
  - `Recency Weight` (up to 20 pts for appearances in 2024–2026)
  - `Syllabus Coverage` (up to 10 pts)
- Avoids false future prediction; exposes full historical evidence trace via `GET /api/evidence/<topic>`.

### 5.3 Study Planner & "What Should I Study Now?" (`services/study_planner_service.py`)
- Formulates highest-yield study action: Opportunity Formula = `((100 - mastery) * 0.65) + (historical_relevance * 0.35)`.
- Displays explicit multi-point **"WHY THIS"** justification based on current mastery, PYQ weightage, and prerequisites.
- **"I'M COOKED 🚨" Mode**: Creates an emergency cram plan maximizing mark density per minute.

### 5.4 Adaptive Diagnostic Quiz (`services/adaptive_quiz_service.py`)
- Dynamically escalates question difficulty upon correct answers (Easy -> Medium -> Hard).
- Shifts to foundational reinforcement on mistakes.
- Updates student topic mastery after every answer.

### 5.5 Rubric-Grounded Answer Evaluator (`services/answer_evaluator.py`)
- Automatically constructs university rubrics for 2, 5, 10, and 15-mark questions.
- Scores submitted answers on technical accuracy, structure, terminology, and diagrams.
- **Exam Answer Mode**: Generates topper-grade exemplar answers with section headers, diagram blocks, and limitations.

### 5.6 AI Viva Voce Room (`services/viva_service.py`)
- Adaptive oral examination with three distinct examiner personas:
  - **Professor**: Formal, academic, mechanism-focused.
  - **Strict Examiner**: Probing, demanding, challenges vague statements.
  - **Friendly Mentor**: Warm, guided, scaffolding support.
- Generates dynamic follow-up questions probing student weaknesses identified in previous oral responses.

### 5.7 Timed Exam Simulator (`services/exam_simulator_service.py`)
- Features live countdown timer, question navigation palette, autosave, and mark-for-review flags.
- Submissions produce comprehensive readiness reports with topic breakdowns and actionable next steps.

---

## 6. REST API Endpoints

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `POST /api/documents/upload` | POST | Universal document ingestion (PDF/TXT/DOCX/PPTX) |
| `POST /api/rag/query` | POST | Evidence-backed question answering with citations |
| `GET /api/mastery/<subject>` | GET | Topic-level mastery distribution and overall score |
| `GET /api/evidence/<topic>` | GET | Historical PYQ occurrences, marks, and questions |
| `GET /api/what-to-study-now` | GET | Single highest-yield learning action with WHY justification |
| `POST /api/study-plan` | POST | Personalized study plan or "I'M COOKED" emergency plan |
| `POST /api/quiz/start` | POST | Initialize adaptive diagnostic quiz |
| `POST /api/quiz/answer` | POST | Submit answer and receive real-time mastery adaptation |
| `POST /api/answer/evaluate` | POST | Rubric-based scoring or exemplar generation |
| `POST /api/viva/start` | POST | Enter Viva Voce oral exam room |
| `POST /api/viva/answer` | POST | Submit viva response and get adaptive follow-up |
| `POST /api/exam/start` | POST | Launch timed practice exam simulation |
| `POST /api/exam/save` | POST | Autosave question response |
| `POST /api/exam/submit` | POST | Submit exam and compute topic breakdown |
| `GET /api/graph/<subject>` | GET | Concept curriculum graph topology |
| `GET /api/dashboard/<subject>` | GET | Unified dashboard payload |
| `POST /api/demo/seed` | POST | Populate benchmark Operating Systems curriculum |

---

## 7. Hackathon Demo Instructions

1. Start the Flask application:
   ```bash
   python app.py
   ```
2. Navigate to `http://localhost:5000/demo` in your browser (or click the yellow **"⚡ LOAD DEMO DATA"** button in the header).
3. The platform instantly initializes the full Operating Systems benchmark curriculum:
   - Topic masteries are populated across Critical, Weak, and Developing bands.
   - Historical PYQs from 2024 to 2026 are indexed with mark weights and Bloom levels.
   - The Concept Graph visualizes curriculum topology.
   - **"WHAT SHOULD I STUDY NOW?"** displays high-yield recommendation for *Deadlocks & Banker's Algorithm*.
   - Launch the **Adaptive Quiz**, **AI Viva Voce**, **I'M COOKED 🚨 Mode**, or **Exam Simulator** for live demonstration.
