import json
import pytest
from app import app
from models.database import init_db
from services.mastery_service import MasteryService, get_mastery_band, get_mastery_color
from services.pyq_service import HistoricalRelevanceService
from services.study_planner_service import StudyPlannerService
from services.adaptive_quiz_service import AdaptiveQuizService
from services.answer_evaluator import AnswerEvaluator
from services.viva_service import VivaService
from services.exam_simulator_service import ExamSimulatorService
from services.knowledge_graph.graph_service import KnowledgeGraphService
from services.llm.base_provider import LLMProvider


class MockLLMProvider(LLMProvider):
    def generate(self, prompt, system_instruction=None, temperature=0.7, max_tokens=None, use_reasoning=False):
        if "viva" in prompt.lower() or "examiner" in prompt.lower():
            return "Explain how the critical section problem is solved using semaphores."
        if "model answer" in prompt.lower() or "exam answer" in prompt.lower():
            return "1. Definition: Process scheduling...\n2. Working: Ready queue...\n3. Diagram: [DIAGRAM: CPU Scheduling]\n4. Example: FCFS vs RR."
        return "Grounded mock response based on Operating Systems curriculum."

    def generate_json(self, prompt, schema=None, system_instruction=None, temperature=0.2, use_reasoning=False):
        if "viva" in prompt.lower() or "oral response" in prompt.lower():
            return json.dumps({
                "score_out_of_10": 8.0,
                "accuracy_summary": "Good conceptual explanation.",
                "identified_weakness": "Needs clarification on starvation edge cases.",
                "examiner_comment": "Well put. How would you prevent starvation?"
            })
        if "rubric" in prompt.lower() or "evaluat" in prompt.lower():
            return json.dumps({
                "score": 8.5,
                "max_score": 10,
                "strengths": ["Accurate definition", "Correct mechanism"],
                "missing_concepts": ["Page table base register"],
                "corrections": ["Clarify virtual address bits"],
                "ideal_structure": ["Definition", "Architecture", "Working"],
                "improvement_advice": ["Use numbered steps"]
            })
        # Default MCQ question
        return json.dumps({
            "question": "What is the primary role of the CPU scheduler?",
            "options": [
                "A. Select ready process for CPU allocation",
                "B. Manage virtual memory page swapping",
                "C. Format physical disk partitions",
                "D. Handle network sockets"
            ],
            "correct_answer": "A. Select ready process for CPU allocation",
            "explanation": "The CPU scheduler selects from among the processes in ready queue."
        })

    def embed(self, texts, model=None):
        return [[0.1] * 768 for _ in texts]

    def health_check(self):
        return {"status": "healthy", "provider": "mock"}


class MockRAG:
    def query(self, question, subject="General", top_k=3):
        return {
            "answer": "Operating systems manage hardware resources through scheduling and memory abstraction.",
            "citations": []
        }


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as c:
        yield c


# ----------------------------------------------------------------
# 1. Mastery Engine Tests
# ----------------------------------------------------------------
def test_mastery_bands():
    assert get_mastery_band(95.0) == "Mastered"
    assert get_mastery_band(80.0) == "Strong"
    assert get_mastery_band(65.0) == "Developing"
    assert get_mastery_band(45.0) == "Weak"
    assert get_mastery_band(25.0) == "Critical"


def test_deterministic_mastery_scoring():
    service = MasteryService()
    import uuid
    topic = f"Test Topic {uuid.uuid4().hex[:6]}"
    # Record initial correct attempt
    res1 = service.record_interaction(
        student_id=9999,
        subject_name="Test Subject",
        topic_name=topic,
        is_correct=True,
        difficulty="Medium",
        response_time_seconds=15.0
    )
    assert res1["attempt_count"] == 1
    assert res1["correct_count"] == 1
    assert 50.0 <= res1["mastery_score"] <= 100.0

    # Record incorrect attempt: score should drop
    res2 = service.record_interaction(
        student_id=9999,
        subject_name="Test Subject",
        topic_name=topic,
        is_correct=False,
        difficulty="Hard",
        response_time_seconds=45.0
    )
    assert res2["attempt_count"] == 2
    assert res2["correct_count"] == 1
    assert res2["mastery_score"] < res1["mastery_score"]


# ----------------------------------------------------------------
# 2. Historical PYQ Relevance Tests
# ----------------------------------------------------------------
def test_pyq_historical_relevance():
    pyq_service = HistoricalRelevanceService()
    mock_questions = [
        {"topic": "Deadlocks", "marks": 10, "year": "2024", "question_number": "Q1", "question": "Explain deadlock conditions."},
        {"topic": "Deadlocks", "marks": 10, "year": "2025", "question_number": "Q2", "question": "Solve Banker's algorithm."},
        {"topic": "Process Scheduling", "marks": 5, "year": "2024", "question_number": "Q3", "question": "Explain FCFS."}
    ]
    intel = pyq_service.index_pyq_analyses("Operating Systems", mock_questions, total_historical_marks=25)
    assert intel["total_questions_analyzed"] == 3
    assert len(intel["topics"]) == 2

    # Deadlocks should be ranked highest due to 2 appearances and 20 total marks
    top_topic = intel["topics"][0]
    assert top_topic["topic"] == "Deadlocks"
    assert top_topic["historical_relevance_score"] >= 65.0
    assert top_topic["relevance_tier"] == "HIGH"
    assert len(top_topic["evidence"]) == 2

    # Test evidence lookup
    ev = pyq_service.get_topic_evidence("Operating Systems", "Deadlocks")
    assert ev["found"] is True
    assert ev["topic_intelligence"]["topic"] == "Deadlocks"


# ----------------------------------------------------------------
# 3. Study Planner & "What Should I Study Now?" Tests
# ----------------------------------------------------------------
def test_what_should_i_study_now():
    planner = StudyPlannerService()
    action = planner.get_what_should_i_study_now(student_id=1, subject_name="Operating Systems", available_minutes=30)
    assert "recommended_topic" in action
    assert "why_explanation" in action
    assert len(action["why_explanation"]) >= 2
    assert action["recommended_minutes"] <= 30
    assert "actions" in action
    assert "START" in action["actions"]["start"]


def test_im_cooked_emergency_planner():
    planner = StudyPlannerService()
    cram_plan = planner.generate_im_cooked_emergency_plan(
        student_id=1,
        subject_name="Operating Systems",
        available_hours=3.0,
        current_prep_level="Zero"
    )
    assert cram_plan["mode"] == "EMERGENCY_CRAM"
    assert cram_plan["total_minutes"] == 180
    assert len(cram_plan["schedule"]) >= 3
    assert "disclaimer" in cram_plan


# ----------------------------------------------------------------
# 4. Adaptive Quiz Engine Tests
# ----------------------------------------------------------------
def test_adaptive_quiz_flow():
    mock_provider = MockLLMProvider()
    quiz_svc = AdaptiveQuizService(provider=mock_provider)
    start_res = quiz_svc.start_adaptive_quiz(student_id=1, subject_name="Operating Systems", total_questions=3)
    session_id = start_res["session_id"]
    assert session_id.startswith("adp_")
    assert start_res["question_number"] == 1
    assert len(start_res["options"]) == 4

    # Process correct answer
    ans_res = quiz_svc.process_answer(
        session_id=session_id,
        selected_option=start_res["options"][0],
        response_time_seconds=10.0
    )
    assert "is_correct" in ans_res
    assert "mastery_update" in ans_res
    assert ans_res["is_finished"] is False


# ----------------------------------------------------------------
# 5. Answer Evaluator Tests
# ----------------------------------------------------------------
def test_answer_evaluator_rubric_and_grading():
    mock_provider = MockLLMProvider()
    mock_rag = MockRAG()
    evaluator = AnswerEvaluator(provider=mock_provider, rag=mock_rag)
    rubric_10 = evaluator.build_rubric("Explain virtual memory", max_marks=10)
    assert rubric_10["max_marks"] == 10
    assert len(rubric_10["expected_sections"]) >= 4

    eval_result = evaluator.evaluate_answer(
        question="Explain virtual memory",
        student_answer="Virtual memory is a memory management technique that allows large processes to execute using paging.",
        max_marks=10,
        subject="Operating Systems"
    )
    assert "score" in eval_result
    assert eval_result["score"] <= 10.0
    assert "strengths" in eval_result
    assert "missing_concepts" in eval_result


def test_exam_answer_mode_exemplar():
    mock_provider = MockLLMProvider()
    evaluator = AnswerEvaluator(provider=mock_provider)
    exemplar = evaluator.generate_exam_answer_template("Explain Round Robin scheduling", marks=5)
    assert exemplar["target_marks"] == 5
    assert len(exemplar["model_answer"]) > 50


# ----------------------------------------------------------------
# 6. Viva Voce Engine Tests
# ----------------------------------------------------------------
def test_viva_session_lifecycle():
    mock_provider = MockLLMProvider()
    viva_svc = VivaService(provider=mock_provider)
    viva_start = viva_svc.start_viva(student_id=1, subject="Operating Systems", topic="Deadlocks", max_questions=2)
    session_id = viva_start["session_id"]
    assert viva_start["question_number"] == 1
    assert len(viva_start["question"]) > 10

    # Submit first answer
    ans_1 = viva_svc.process_answer(session_id=session_id, student_answer="Deadlock occurs when processes hold resources and wait for others in a circular chain.")
    assert ans_1["is_finished"] is False
    assert "next_question" in ans_1

    # Submit second and final answer
    ans_2 = viva_svc.process_answer(session_id=session_id, student_answer="Banker's algorithm checks safety before allocating resources.")
    assert ans_2["is_finished"] is True
    assert "final_report" in ans_2
    assert ans_2["final_report"]["average_score"] > 0


# ----------------------------------------------------------------
# 7. Exam Simulator Tests
# ----------------------------------------------------------------
def test_exam_simulator_session():
    sim = ExamSimulatorService()
    mock_paper = {
        "title": "OS Unit Test",
        "total_marks": 20,
        "sections": [
            {
                "section_title": "Section A",
                "questions": [
                    {"question_number": "Q1", "question_text": "Define process.", "marks": 5, "topic": "Process State Transitions"},
                    {"question_number": "Q2", "question_text": "Explain paging.", "marks": 15, "topic": "Paging & Segmentation"}
                ]
            }
        ]
    }
    exam_start = sim.start_exam(student_id=1, paper_data=mock_paper, duration_minutes=30)
    session_id = exam_start["session_id"]
    assert exam_start["total_questions"] == 2

    # Save question response
    save_res = sim.save_question_response(session_id=session_id, question_id="q_1", answer_text="A process is a program in execution.", marked_for_review=False)
    assert save_res["saved"] is True
    assert save_res["answered_count"] == 1

    # Submit exam
    submit_res = sim.submit_exam(session_id=session_id)
    assert "score" in submit_res
    assert submit_res["total_marks"] == 20
    assert len(submit_res["topic_breakdown"]) == 2
    assert "recommended_next_actions" in submit_res


# ----------------------------------------------------------------
# 8. REST API Endpoints Integration Tests
# ----------------------------------------------------------------
def test_api_mastery_endpoint(client):
    res = client.get("/api/mastery/Operating%20Systems")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert "overall_mastery" in json_data["data"]


def test_api_what_to_study_now_endpoint(client):
    res = client.get("/api/what-to-study-now?subject=Operating%20Systems")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert "recommended_topic" in json_data["data"]


def test_api_demo_seed_endpoint(client):
    res = client.post("/api/demo/seed")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "success"
