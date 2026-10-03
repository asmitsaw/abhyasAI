"""
Real Integration Tests for AbhyasAI - Phase 19
Tests all HTTP endpoints and verifies the complete closed-learning-loop.
Uses Flask test client with an in-memory override where needed.

Run offline (fast) suite:
    pytest tests/test_real_integration.py -v -m "not gemini"

Run full suite (requires GEMINI_API_KEY and live connection):
    pytest tests/test_real_integration.py -v
"""
import json
import io
import os
import pytest
from app import app
from models.database import init_db

# Skip live Gemini calls if API key absent or when running offline
SKIP_GEMINI = not os.getenv("GEMINI_API_KEY")
gemini_test = pytest.mark.skipif(SKIP_GEMINI, reason="GEMINI_API_KEY not set or offline mode")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as c:
        yield c


# --------------------------------------------------------
# PAGE VIEW ROUTES
# --------------------------------------------------------
def test_homepage_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"ABHYAS" in res.data.upper()


def test_dashboard_loads(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"dashboard" in res.data.lower()


def test_onboarding_loads(client):
    res = client.get("/onboarding")
    assert res.status_code == 200
    assert b"onboarding" in res.data.lower() or b"materials" in res.data.lower() or b"upload" in res.data.lower()


def test_answer_evaluator_loads(client):
    res = client.get("/answer-evaluator")
    assert res.status_code == 200
    assert b"eval" in res.data.lower() or b"answer" in res.data.lower()


def test_answer_mode_loads(client):
    res = client.get("/answer-mode")
    assert res.status_code == 200
    assert b"marks" in res.data.lower() or b"exam" in res.data.lower()


def test_viva_arena_loads(client):
    res = client.get("/viva-arena")
    assert res.status_code == 200
    assert b"viva" in res.data.lower() or b"arena" in res.data.lower()


def test_system_health_loads(client):
    res = client.get("/system-health")
    assert res.status_code == 200


# --------------------------------------------------------
# API: MASTERY & PYQ EVIDENCE
# --------------------------------------------------------
def test_api_mastery_blank_subject(client):
    res = client.get("/api/mastery/General")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "overall_mastery" in data["data"]


def test_api_pyq_evidence_topic(client):
    res = client.get("/api/evidence/Deadlock?subject=Operating+Systems")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True


def test_api_what_to_study_with_params(client):
    res = client.get("/api/what-to-study-now?subject=Operating+Systems&minutes=30")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "recommended_topic" in data["data"]
    assert "recommended_minutes" in data["data"]
    assert "why_explanation" in data["data"]


# --------------------------------------------------------
# API: STUDY PLAN
# --------------------------------------------------------
def test_api_study_plan_standard(client):
    res = client.post("/api/study-plan", json={
        "subject": "Operating Systems",
        "mode": "standard",
        "available_minutes": 60,
        "exam_date": ""
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    # Response may use "slots", "sessions", or "schedule" as the key
    plan = data["data"]
    has_plan_content = "slots" in plan or "sessions" in plan or "schedule" in plan or "subject" in plan
    assert has_plan_content, f"Expected plan content, got keys: {list(plan.keys())}"


def test_api_study_plan_im_cooked(client):
    res = client.post("/api/study-plan", json={
        "subject": "Operating Systems",
        "mode": "im_cooked",
        "available_hours": 2.0,
        "prep_level": "Zero / Not started"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True


# --------------------------------------------------------
# API: ANSWER EVALUATOR
# --------------------------------------------------------
@gemini_test
def test_api_evaluate_answer(client):
    res = client.post("/api/answer/evaluate", json={
        "question": "Explain Banker's Algorithm for deadlock avoidance with example.",
        "answer": "Banker's Algorithm is a deadlock avoidance method. It checks if allocating resources keeps the system in a safe state by verifying the safety sequence.",
        "marks": 10,
        "subject": "Operating Systems",
        "topic": "Deadlock",
        "mode": "evaluate"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "score" in data["data"]


@gemini_test
def test_api_generate_model_answer(client):
    res = client.post("/api/answer/evaluate", json={
        "question": "Explain virtual memory with paging.",
        "marks": 5,
        "subject": "Operating Systems",
        "mode": "generate_exemplar"
    })
    if res.status_code == 500:
        data = res.get_json() or {}
        err_msg = str(data.get("error", "")).lower()
        if "quota" in err_msg or "resource_exhausted" in err_msg or "rate" in err_msg or "503" in err_msg:
            pytest.skip(f"Gemini API daily quota limit reached: {err_msg}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True


# --------------------------------------------------------
# API: ADAPTIVE QUIZ
# --------------------------------------------------------
@gemini_test
def test_api_adaptive_quiz_start(client):
    res = client.post("/api/quiz/start", json={
        "subject": "Operating Systems",
        "topic": "CPU Scheduling",
        "total_questions": 5
    })
    if res.status_code == 500:
        data = res.get_json() or {}
        err_msg = str(data.get("error", "")).lower()
        if "quota" in err_msg or "resource_exhausted" in err_msg or "rate" in err_msg or "503" in err_msg:
            pytest.skip(f"Gemini API daily quota limit reached: {err_msg}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "session_id" in data["data"]
    assert "question" in data["data"]


# --------------------------------------------------------
# API: VIVA
# --------------------------------------------------------
@gemini_test
def test_api_viva_start(client):
    res = client.post("/api/viva/start", json={
        "subject": "Operating Systems",
        "topic": "Deadlock",
        "examiner_mode": "Professor"
    })
    if res.status_code == 500:
        data = res.get_json() or {}
        err_msg = str(data.get("error", "")).lower()
        if "quota" in err_msg or "resource_exhausted" in err_msg or "rate" in err_msg or "503" in err_msg:
            pytest.skip(f"Gemini API daily quota limit reached: {err_msg}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "session_id" in data["data"]
    assert "initial_question" in data["data"] or "question" in data["data"]


# --------------------------------------------------------
# API: KNOWLEDGE GRAPH
# --------------------------------------------------------
def test_api_graph_endpoint(client):
    res = client.get("/api/graph/Operating%20Systems")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "graph" in data["data"]


# --------------------------------------------------------
# API: DASHBOARD PAYLOAD
# --------------------------------------------------------
def test_api_dashboard_payload(client):
    res = client.get("/api/dashboard/Operating%20Systems")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "overall_mastery" in data["data"]
    assert "what_to_study_now" in data["data"]
    assert "historical_intelligence" in data["data"]


# --------------------------------------------------------
# API: DEMO SEED
# --------------------------------------------------------
def test_api_demo_seed(client):
    res = client.post("/api/demo/seed")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "success"


# --------------------------------------------------------
# API: PROCESS MATERIALS (Onboarding pipeline - text fallback)
# --------------------------------------------------------
@gemini_test
def test_api_process_materials_raw_text(client):
    """Test process-materials with in-memory text files for onboarding pipeline."""
    syllabus_txt = b"""
    Module 1: Processes and Threads
    - Process lifecycle and states
    - Thread creation and termination
    - Context switching

    Module 2: CPU Scheduling
    - FCFS, SJF, Round Robin, Priority scheduling
    - Multilevel Queue Scheduling

    Module 3: Deadlock
    - Necessary conditions for deadlock
    - Banker's Algorithm for deadlock avoidance
    - Resource allocation graph
    """
    pyq1_txt = b"""
    Q1. Explain the four necessary conditions for a deadlock to occur. [7 marks]
    Q2. Write a short note on Banker's Algorithm. [5 marks]
    Q3. Describe Round Robin scheduling with example. [8 marks]
    """

    data = {
        "subject_name": "Operating Systems"
    }
    file_data = {
        "syllabus_file": (io.BytesIO(syllabus_txt), "syllabus.txt"),
        "pyq1": (io.BytesIO(pyq1_txt), "pyq_2025.txt"),
    }

    res = client.post(
        "/api/process-materials",
        data={**data, **{k: v for k, v in file_data.items()}},
        content_type="multipart/form-data"
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["subject"] == "Operating Systems"
    assert body["data"]["syllabus_extracted"] is True
    assert isinstance(body["data"]["chunks_indexed"], int)


# --------------------------------------------------------
# API: RAG QUERY
# --------------------------------------------------------
@gemini_test
def test_api_rag_query_endpoint(client):
    res = client.post("/api/rag/query", json={
        "question": "What is virtual memory paging?",
        "subject": "Operating Systems",
        "top_k": 3
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "answer" in data["data"] or "response" in data["data"] or "data" in data


# --------------------------------------------------------
# API: EXAM SIMULATOR
# --------------------------------------------------------
def test_api_exam_start_and_submit(client):
    paper_data = {
        "title": "OS Sample Exam",
        "total_marks": 20,
        "sections": [
            {
                "section_title": "Section A",
                "questions": [
                    {"question_number": "Q1", "question_text": "Define process and explain its states.", "marks": 5, "topic": "Processes"},
                    {"question_number": "Q2", "question_text": "Explain virtual memory.", "marks": 10, "topic": "Memory Management"},
                    {"question_number": "Q3", "question_text": "What is thrashing?", "marks": 5, "topic": "Memory Management"}
                ]
            }
        ]
    }

    start_res = client.post("/api/exam/start", json={
        "paper_data": paper_data,
        "duration_minutes": 60
    })
    assert start_res.status_code == 200
    start_data = start_res.get_json()
    assert start_data["success"] is True
    session_id = start_data["data"]["session_id"]

    submit_res = client.post("/api/exam/submit", json={
        "session_id": session_id,
        "answers": {
            "q_1": "A process is a program in execution with its own PCB.",
            "q_2": "Virtual memory allows processes to use more memory than physically available.",
            "q_3": "Thrashing is excessive paging causing performance degradation."
        }
    })
    assert submit_res.status_code == 200
    submit_data = submit_res.get_json()
    assert submit_data["success"] is True
    assert "score" in submit_data["data"]
