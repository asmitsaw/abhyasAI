# ⚡ AbhyasAI — University Exam Intelligence & Personalized Learning System

> **"Don't just study more. Study what matters next."**

AbhyasAI transforms academic preparation into a closed, intelligent feedback loop. Rather than just generating static quizzes, it understands the university syllabus, historical question patterns, marks distribution, and student concept mastery to continuously guide: **"WHAT SHOULD THIS STUDENT STUDY NEXT?"**

---

## 🌟 Key Features

### 1. 🎯 "What Should I Study Now?"
- Evaluates the gap between historical PYQ importance and current student concept mastery.
- Delivers the single highest-yield study action with multi-point **"WHY THIS"** justification.

### 2. 🚨 "I'M COOKED" Mode
- Emergency exam cramming generator for students with under 24 hours until an exam.
- Maximizes marks yield per minute based on historical question paper density and prerequisite chains.

### 3. 🧠 Modular RAG Engine (`services/rag/`)
- Universal document ingestion for **PDF**, **TXT**, **Markdown**, **DOCX**, **PPTX**, and **YouTube transcripts**.
- Structure-aware chunking preserving modules, topics, and question numbers.
- Persistent **ChromaDB** vector storage with hybrid semantic and keyword reranking.
- Grounded citations `[1]`, `[2]` linking answers directly to source documents with zero hallucination.

### 4. 📊 Deterministic Mastery Engine (`services/mastery_service.py`)
- Calculates 0–100 mastery based on actual student performance, question difficulty, volume consistency, and response times.
- Visualized across five intuitive bands: **Critical**, **Weak**, **Developing**, **Strong**, and **Mastered**.

### 5. 📈 Historical PYQ Intelligence (`services/pyq_service.py`)
- Analyzes past year papers to compute empirical **Historical Relevance Scores**.
- Tracks question frequency, marks percentage, recency (2024–2026), and Bloom's taxonomy levels.

### 6. 🎤 AI Viva Voce Room (`services/viva_service.py`)
- Interactive oral examination with adaptive examiner personas: **Professor**, **Strict Examiner**, and **Friendly Mentor**.
- Dynamically probes student weaknesses identified in preceding oral answers.

### 7. 📝 Answer Evaluator & Exam Answer Mode (`services/answer_evaluator.py`)
- Objective rubric grading for 2, 5, 10, and 15-mark questions.
- Generates topper-grade model answers formatted with diagram specifications and section headers.

### 8. ⏱️ Timed Exam Simulator (`services/exam_simulator_service.py`)
- Interactive test environment with countdown timer, question navigation palette, autosave, and mark-for-review.
- Produces comprehensive post-exam readiness reports with topic breakdowns.

### 9. 🎥 YouTube Lecture Study Lab
- Ingests video transcripts to generate 20-question multiple-choice quizzes with explanations and real-time AI Tutor doubt clearing.

---

## 🚀 Quick Start

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/DhruvGharat/Aabhyas-AI.git
cd Aabhyas-AI
python -m venv venv
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
LLM_PROVIDER=gemini
DATABASE_URL=sqlite:///abhyas.db
DEMO_MODE=true
```

### 4. Run the Application
```bash
python app.py
```
Open your browser at `http://localhost:5000`.

---

## ⚡ Instant Demo Mode

To run a complete demonstration without uploading documents or waiting for API keys:
1. Navigate to `http://localhost:5000/demo` (or click **"⚡ LOAD DEMO DATA"** on the dashboard).
2. Operating Systems benchmark curriculum, past year papers (2024–2026), topic masteries, and concept graphs are instantly populated.
3. Explore the **Dashboard**, **"What Should I Study Now?"**, **Adaptive Quiz**, **AI Viva**, and **I'M COOKED Mode**.

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```

---

## 📁 Project Architecture

```
AbhyasAI/
├── app.py                     # Main Flask server & route handlers
├── config/config.py           # Configuration manager
├── models/
│   ├── database.py            # SQLAlchemy database models & session
│   ├── exam_models.py         # Pydantic schemas for exams & syllabi
│   └── ...
├── routes/
│   ├── api_routes.py          # Unified REST API endpoints
│   ├── exam_routes.py         # Exam prep paper generator blueprint
│   ├── learning_routes.py     # Learning lab blueprint
│   └── viva_routes.py         # Viva Voce oral exam blueprint
├── services/
│   ├── llm/                   # LLM Provider Abstraction (Gemini, Local, Auto)
│   ├── rag/                   # Modular RAG (Ingestion, Chunking, Retrieval, Citations)
│   ├── knowledge_graph/       # Concept graph topology & prerequisite services
│   ├── mastery_service.py     # Deterministic 0-100 student mastery engine
│   ├── pyq_service.py         # Historical PYQ relevance & evidence analytics
│   ├── study_planner_service.py # "What Should I Study Now?" & "I'M COOKED 🚨"
│   ├── adaptive_quiz_service.py # Progressive difficulty testing engine
│   ├── answer_evaluator.py    # Rubric-based answer evaluation & model answers
│   ├── viva_service.py        # Adaptive oral examiner state machine
│   ├── exam_simulator_service.py # Interactive timed mock exam environment
│   └── demo_service.py        # Benchmark demo seed data
├── templates/
│   ├── dashboard.html         # Unified exam intelligence dashboard
│   ├── index.html             # Neobrutalist landing page
│   ├── learning/learn.html    # YouTube lecture quiz & AI tutor lab
│   └── exam/prep.html         # Exam blueprint & practice paper generator
└── tests/
    ├── test_all_subsystems.py # Full subsystem integration test suite
    └── test_rag.py            # RAG ingestion, chunking, and retrieval tests
```

---

## 📄 License
MIT License. Built for students to study smarter, not harder! 💥
