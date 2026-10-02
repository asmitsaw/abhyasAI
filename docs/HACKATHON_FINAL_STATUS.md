# 🏆 ABHYASAI — HACKATHON FINAL STATUS REPORT

> **System:** AbhyasAI — AI Exam Intelligence & Personalized Learning System  
> **Stack:** Python · Flask · Google Gemini API · ChromaDB · SQLAlchemy · Pydantic  
> **Status:** ✅ HACKATHON READY

---

## ✅ TEST SUITE STATUS

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_rag.py` | 9 | ✅ ALL PASSING |
| `tests/test_all_subsystems.py` | 13 | ✅ ALL PASSING |
| `tests/test_real_integration.py` | 30 | ✅ ALL PASSING |
| **TOTAL** | **52** | **✅ 52 PASSING** |

---

## 🔗 LIVE ENDPOINTS

| Route | Description |
|-------|-------------|
| `GET /` | Hero landing page with closed-loop value chain |
| `GET /dashboard` | Master intelligence dashboard |
| `GET /onboarding` | Upload Materials → RAG ingestion pipeline |
| `GET /answer-evaluator` | 4-metric rubric answer evaluator |
| `GET /answer-mode` | 2/5/10/15 mark exam answer generator |
| `GET /viva-arena` | Full-screen AI oral examination with voice input |
| `GET /system-health` | System diagnostics |
| `GET /learn` | YouTube lecture → AI Tutor |
| `GET /exam` | Exam blueprint + practice paper generator |
| `GET /demo` | Seeds benchmark OS data → redirects to dashboard |

---

## 🧠 INTELLIGENCE APIS

| Endpoint | Purpose |
|----------|---------|
| `GET /api/mastery/<subject>` | Deterministic mastery score across 5 bands |
| `GET /api/evidence/<topic>` | Historical PYQ relevance score per topic |
| `GET /api/what-to-study-now` | Highest-yield next action for student |
| `POST /api/study-plan` | Standard or I'M COOKED emergency plan |
| `POST /api/quiz/start` | Adaptive quiz with live difficulty scaling |
| `POST /api/quiz/answer` | Real-time quiz answer + mastery update |
| `POST /api/answer/evaluate` | Rubric-based answer scoring |
| `POST /api/answer/evaluate` (exemplar mode) | Model topper answer generation |
| `POST /api/viva/start` | AI Viva with 3 examiner personas |
| `POST /api/viva/answer` | Submit oral response → follow-up |
| `POST /api/exam/start` | Interactive timed exam session |
| `POST /api/exam/save` | Autosave question response |
| `POST /api/exam/submit` | Final exam submission + grading |
| `GET /api/graph/<subject>` | Concept knowledge graph |
| `GET /api/dashboard/<subject>` | Unified dashboard payload |
| `POST /api/demo/seed` | Seed OS benchmark data |
| `POST /api/process-materials` | **Onboarding: parse files → ChromaDB → mastery init** |
| `POST /api/documents/upload` | Single document upload to RAG |
| `POST /api/rag/query` | RAG-grounded question answering |

---

## 🏗️ ARCHITECTURE

```
Student Uploads (Syllabus, PYQs, Notes)
        │
        ▼
[Onboarding Pipeline: /api/process-materials]
        │
        ├── PDF/DOCX/PPTX/TXT Parsing
        ├── Structure-Aware Chunking (section-aware, 400-token chunks)
        ├── ChromaDB Vector Store (cosine similarity, persistent)
        │   └── Gemini Embedding Model: gemini-embedding-001 (3072 dims)
        ├── Syllabus Topic Extraction (Gemini LLM → Pydantic Syllabus model)
        ├── PYQ Pattern Extraction (regex + topic matching)
        ├── Historical Relevance Service (frequency × recency × marks weight)
        └── SQLite Mastery Init (StudentTopicMastery rows, default 45%)
        
         INTELLIGENCE LOOP:
         
[/api/what-to-study-now]  ←  MasteryService + HistoricalRelevanceService
        │
        ▼
[Student Practice] — Quiz / Viva / Exam Simulator / Answer Evaluator
        │
        ▼
[Mastery Update] — deterministic score recalculation
        │
        ▼
[/api/dashboard/<subject>] — live readiness, PYQ heatmap, concept graph
```

---

## 🎯 CLOSED LEARNING LOOP

```
Syllabus + PYQs + Notes
        ↓ RAG ingestion (ChromaDB)
Historical PYQ Intelligence Matrix
        ↓ relevance scoring
What Should I Study Now? (evidence-grounded)
        ↓ student acts
Adaptive Quiz / AI Viva / Exam Simulator
        ↓ answers evaluated
Rubric Scoring (4 metrics)
        ↓ results fed back
Mastery Re-estimation (deterministic, 5-band)
        ↓ display
Dashboard: Readiness % → repeats
```

---

## 🎨 UI PAGES IMPLEMENTED

- **Dashboard**: Readiness gauge, What to Study Now card, Evidence Drawer, Concept Graph SVG, Mastery Heatmap, PYQ Weightage, I'M COOKED modal, AI Viva modal, 3-Minute Tour, Before→After Demo
- **Onboarding**: Step-by-step timeline with real 8-step backend pipeline
- **Answer Evaluator**: 4-metric (Content, Structure, Technical, Completeness) with rubric breakdown
- **Exam Answer Mode**: 2/5/10/15 mark calibrated model answers with copy + download
- **Viva Arena**: Full-screen with persona selection, live countdown timer, speech recognition, final report
- **System Health**: Live diagnostics with API key status, ChromaDB, DB rows
- **Learning Lab**: YouTube URL → transcript → 20-question quiz + AI Tutor

---

## 🔧 TECH STACK SUMMARY

| Layer | Technology |
|-------|-----------|
| Web Framework | Flask 3.x + Blueprints |
| LLM | Google Gemini 2.0 Flash (via `google-genai`) |
| Embeddings | `gemini-embedding-001` (3072 dims) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Relational DB | SQLite via SQLAlchemy (8 tables) |
| Parsing | pypdf, python-docx, python-pptx |
| YouTube | youtube-transcript-api |
| Validation | Pydantic v2 |
| Testing | pytest (52 tests) |
| UI Design | Neobrutalist comic-book style (custom CSS tokens) |

---

## 🚀 DEMO SEQUENCE (3 Minutes)

1. **Click "⚡ BEFORE → AFTER DEMO"** on dashboard → watch readiness animate from 47% → 73%
2. **Click "🚩 3-MIN TOUR"** → step through all 7 core features
3. **Click "SHOW EVIDENCE 🔍"** → Evidence Drawer with grounded PYQ citations
4. **Upload materials at `/onboarding`** → watch real ChromaDB indexing pipeline
5. **Enter Viva Arena** → choose Strict Examiner, speak your answers via microphone
6. **Try Answer Evaluator** → paste a 10-mark answer and get 4-metric rubric breakdown
7. **Generate Model Answer** at Exam Answer Mode → download 10-mark topper answer

---

## ⚠️ SECURITY GUARDRAILS

- No hallucinated "exam predictions" — all recommendations cite empirical PYQ occurrence counts
- Mastery score is deterministic (mathematical formula), not LLM-generated
- Every recommendation displays `WHY THIS?` with sourced evidence (year, question number, marks)
- System Health page discloses data sources and confidence levels

---

> Generated by AbhyasAI Hackathon Build System — All 52 tests verified passing.
