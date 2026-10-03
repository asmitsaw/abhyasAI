import os
import re
import time
from flask import Blueprint, request, jsonify, session
from models.database import SessionLocal, User, Subject, StudentTopicMastery
from services.rag.rag_pipeline import get_rag_pipeline
from services.rag.ingestion import UniversalIngestionService
from services.mastery_service import MasteryService
from services.pyq_service import get_pyq_service
from services.study_planner_service import StudyPlannerService
from services.adaptive_quiz_service import AdaptiveQuizService
from services.answer_evaluator import AnswerEvaluator
from services.viva_service import get_viva_service
from services.exam_simulator_service import get_exam_simulator
from functools import wraps
from typing import Optional, Dict, Any, List
from services.knowledge_graph.graph_service import get_knowledge_graph_service
from services.demo_service import seed_demo_data
from services.supabase_service import get_supabase_service
from services.ingestion import get_ingestion_manager

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Instantiate services
ingestion_service = UniversalIngestionService()
ingestion_manager = get_ingestion_manager()
supabase_service = get_supabase_service()
rag_pipeline = get_rag_pipeline()
mastery_service = MasteryService()
pyq_service = get_pyq_service()
study_planner = StudyPlannerService(mastery_service)
adaptive_quiz = AdaptiveQuizService(mastery_service)
answer_evaluator = AnswerEvaluator()
viva_service = get_viva_service()
exam_simulator = get_exam_simulator()
kg_service = get_knowledge_graph_service()


def get_authenticated_user(allow_demo: bool = False) -> Optional[Dict[str, Any]]:
    """
    Extract and verify user identity from Authorization Bearer token, session cookie,
    or fallback to session store. Never trust raw user_id in request bodies.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else ""
    if not token:
        token = request.cookies.get("abhyas_auth_token", "")

    if token:
        user = supabase_service.verify_token(token)
        if user:
            return user

    if "user_id" in session:
        return {"id": str(session["user_id"]), "email": session.get("user_email", "student@abhyas.ai")}

    # Demo mode fallback only when explicitly permitted
    if allow_demo and os.getenv("DEMO_MODE", "false").lower() == "true":
        demo_id = str(session.get("student_id", "demo_student_01"))
        return {"id": demo_id, "email": "demo@abhyas.ai"}

    return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_authenticated_user(allow_demo=False)
        if not user:
            return jsonify({
                "success": False,
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Authentication required. Please log in."
                }
            }), 401
        return f(user, *args, **kwargs)
    return decorated


def get_current_student_id() -> int:
    return int(session.get("student_id", 1))


def generate_chat_title(question: str) -> str:
    """Generate clean deterministic title from user question without expensive LLM call."""
    cleaned = re.sub(r'^(what is|explain|define|how to|tell me about|describe|can you explain)\s+', '', question.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'[?!.,;:]+', '', cleaned).strip()
    words = cleaned.split()
    if not words:
        return "Study Discussion"
    return " ".join(words[:6]).title()


# -------------------------------------------------------------
# 1. RAG & Document Ingestion APIs
# -------------------------------------------------------------
@api_bp.route("/documents/upload", methods=["POST"])
def upload_document():
    try:
        subject = request.form.get("subject", "General").strip()
        doc_type = request.form.get("document_type", "notes").strip()
        year = request.form.get("year", "").strip()

        # Check uploaded file
        uploaded_file = request.files.get("file")
        pasted_text = request.form.get("text", "").strip()

        if uploaded_file and uploaded_file.filename:
            res = ingestion_service.ingest_document(
                file_source=uploaded_file.stream,
                filename=uploaded_file.filename,
                document_type=doc_type,
                subject=subject,
                year=year
            )
            return jsonify({"success": True, "data": res})
        elif pasted_text:
            title = request.form.get("title", f"Pasted {doc_type.capitalize()}")
            res = ingestion_service.ingest_raw_text(
                text=pasted_text,
                title=title,
                document_type=doc_type,
                subject=subject,
                year=year
            )
            return jsonify({"success": True, "data": res})
        else:
            return jsonify({"success": False, "error": "Please provide a document file or text content."}), 400

    except Exception as error:
        print(f"[API Upload Error]: {error}")
        return jsonify({"success": False, "error": f"Failed to process document: {str(error)}"}), 500


@api_bp.route("/rag/query", methods=["POST"])
def query_rag():
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        subject = data.get("subject", "General").strip()

        if not question:
            return jsonify({"success": False, "error": "Please provide a question."}), 400

        result = rag_pipeline.query(
            question=question,
            subject=subject,
            document_type=data.get("document_type") or None,
            top_k=int(data.get("top_k", 5)),
            use_reasoning=bool(data.get("use_reasoning", False))
        )
        return jsonify({"success": True, "data": result})

    except Exception as error:
        print(f"[API RAG Error]: {error}")
        return jsonify({"success": False, "error": f"Query processing error: {str(error)}"}), 500


# -------------------------------------------------------------
# 2. Mastery & PYQ Evidence APIs
# -------------------------------------------------------------
@api_bp.route("/mastery/<subject>", methods=["GET"])
def get_mastery(subject):
    try:
        student_id = get_current_student_id()
        data = mastery_service.get_subject_mastery(student_id=student_id, subject_name=subject)
        return jsonify({"success": True, "data": data})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/evidence/<topic>", methods=["GET"])
def get_topic_evidence(topic):
    try:
        subject = request.args.get("subject", "Operating Systems")
        data = pyq_service.get_topic_evidence(subject_name=subject, topic_name=topic)
        return jsonify({"success": True, "data": data})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 3. Study Planner & "What Should I Study Now?"
# -------------------------------------------------------------
@api_bp.route("/what-to-study-now", methods=["GET"])
def what_should_i_study_now():
    try:
        student_id = get_current_student_id()
        subject = request.args.get("subject", "Operating Systems")
        available_mins = int(request.args.get("minutes", 45))

        action = study_planner.get_what_should_i_study_now(
            student_id=student_id,
            subject_name=subject,
            available_minutes=available_mins
        )
        return jsonify({"success": True, "data": action})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/study-plan", methods=["POST"])
def create_study_plan():
    try:
        data = request.get_json() or {}
        student_id = get_current_student_id()
        subject = data.get("subject", "Operating Systems")
        mode = data.get("mode", "standard")

        if mode == "im_cooked":
            hours = float(data.get("available_hours", 4.0))
            prep_level = data.get("prep_level", "Zero")
            plan = study_planner.generate_im_cooked_emergency_plan(
                student_id=student_id,
                subject_name=subject,
                available_hours=hours,
                current_prep_level=prep_level
            )
        else:
            mins = int(data.get("available_minutes", 90))
            exam_date = data.get("exam_date", "")
            plan = study_planner.generate_personalized_study_plan(
                student_id=student_id,
                subject_name=subject,
                available_minutes=mins,
                exam_date_str=exam_date
            )

        return jsonify({"success": True, "data": plan})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 4. Adaptive Quiz APIs
# -------------------------------------------------------------
@api_bp.route("/quiz/start", methods=["POST"])
def start_adaptive_quiz():
    try:
        data = request.get_json() or {}
        student_id = get_current_student_id()
        subject = data.get("subject", "Operating Systems")
        topic = data.get("topic", "").strip()
        if not topic:
            topic = study_planner.get_what_should_i_study_now(
                student_id=student_id,
                subject_name=subject,
                available_minutes=25,
            ).get("recommended_topic", "Core Concepts")
        total_q = int(data.get("total_questions", 8))

        res = adaptive_quiz.start_adaptive_quiz(
            student_id=student_id,
            subject_name=subject,
            topic_name=topic,
            total_questions=total_q
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/quiz/answer", methods=["POST"])
def answer_adaptive_quiz():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        selected_option = data.get("selected_option", "")
        time_spent = float(data.get("response_time", 15.0))

        if not session_id or not selected_option:
            return jsonify({"success": False, "error": "session_id and selected_option are required."}), 400

        res = adaptive_quiz.process_answer(
            session_id=session_id,
            selected_option=selected_option,
            response_time_seconds=time_spent
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 5. Answer Evaluator & Exam Answer Mode
# -------------------------------------------------------------
@api_bp.route("/answer/evaluate", methods=["POST"])
def evaluate_student_answer():
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()
        marks = int(data.get("marks", 10))
        subject = data.get("subject", "Operating Systems")
        topic = data.get("topic", "")

        mode = data.get("mode", "evaluate")
        if mode == "generate_exemplar":
            res = answer_evaluator.generate_exam_answer_template(
                question=question,
                marks=marks,
                subject=subject
            )
        else:
            if not question or not answer:
                return jsonify({"success": False, "error": "question and answer are required."}), 400
            res = answer_evaluator.evaluate_answer(
                question=question,
                student_answer=answer,
                max_marks=marks,
                subject=subject,
                topic=topic
            )

        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 6. Viva Voce APIs
# -------------------------------------------------------------
@api_bp.route("/viva/start", methods=["POST"])
def start_viva():
    try:
        data = request.get_json() or {}
        student_id = get_current_student_id()
        subject = data.get("subject", "Operating Systems")
        topic = data.get("topic", "Process Management")
        mode = data.get("examiner_mode", "Professor")

        res = viva_service.start_viva(
            student_id=student_id,
            subject=subject,
            topic=topic,
            examiner_mode=mode
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/viva/answer", methods=["POST"])
def answer_viva():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        answer_text = data.get("answer", "").strip()

        if not session_id or not answer_text:
            return jsonify({"success": False, "error": "session_id and answer are required."}), 400

        res = viva_service.process_answer(
            session_id=session_id,
            student_answer=answer_text
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 7. Interactive Exam Simulator APIs
# -------------------------------------------------------------
@api_bp.route("/exam/start", methods=["POST"])
def start_exam_simulation():
    try:
        data = request.get_json() or {}
        student_id = get_current_student_id()
        paper_data = data.get("paper_data", {})
        duration = int(data.get("duration_minutes", 60))

        res = exam_simulator.start_exam(
            student_id=student_id,
            paper_data=paper_data,
            duration_minutes=duration
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/exam/save", methods=["POST"])
def save_exam_progress():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        q_id = data.get("question_id")
        answer_text = data.get("answer", "")
        review = bool(data.get("marked_for_review", False))

        res = exam_simulator.save_question_response(
            session_id=session_id,
            question_id=q_id,
            answer_text=answer_text,
            marked_for_review=review
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/exam/submit", methods=["POST"])
def submit_exam_simulation():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        answers = data.get("answers", {})

        res = exam_simulator.submit_exam(
            session_id=session_id,
            submitted_answers=answers
        )
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 8. Knowledge Graph & Unified Dashboard APIs
# -------------------------------------------------------------
@api_bp.route("/graph/<subject>", methods=["GET"])
def get_knowledge_graph(subject):
    try:
        student_id = get_current_student_id()
        data = kg_service.get_subject_graph(student_id=student_id, subject_name=subject)
        return jsonify({"success": True, "data": data})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@api_bp.route("/dashboard/<subject>", methods=["GET"])
def get_dashboard_payload(subject):
    try:
        student_id = get_current_student_id()
        mastery = mastery_service.get_subject_mastery(student_id, subject)
        action = study_planner.get_what_should_i_study_now(student_id, subject)
        pyq_intel = pyq_service.get_subject_intelligence(subject)

        return jsonify({
            "success": True,
            "data": {
                "subject": subject,
                "overall_mastery": mastery.get("overall_mastery", 0.0),
                "overall_band": mastery.get("overall_band", "Critical"),
                "topics": mastery.get("topics", []),
                "what_to_study_now": action,
                "historical_intelligence": pyq_intel
            }
        })
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 9. Demo Mode Seed API
# -------------------------------------------------------------
@api_bp.route("/demo/seed", methods=["POST"])
def trigger_demo_seed():
    try:
        res = seed_demo_data()
        return jsonify({"success": True, "data": res})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# -------------------------------------------------------------
# 10. Real Material Processing & Onboarding Pipeline
# -------------------------------------------------------------
@api_bp.route("/process-materials", methods=["POST"])
def process_materials():
    db = SessionLocal()
    try:
        started_at = time.perf_counter()
        student_id = get_current_student_id()
        subject_name = (
            request.form.get("subject_name", "").strip()
            or request.form.get("subject", "").strip()
            or "Operating Systems"
        )
        session["current_subject"] = subject_name
        indexing_warnings = []

        def safe_ingest(file_source, filename, document_type, subject, year=""):
            try:
                return ingestion_service.ingest_document(
                    file_source=file_source,
                    filename=filename,
                    document_type=document_type,
                    subject=subject,
                    year=year
                )
            except Exception as ingest_err:
                indexing_warnings.append(
                    f"{document_type.upper()} indexing skipped for '{filename}': {str(ingest_err)}"
                )
                return {"chunks_created": 0, "status": "indexing_skipped"}

        # 1. Ingest Syllabus
        syllabus_file = request.files.get("syllabus_file")
        syllabus_chunks = 0
        detected_topics = []
        syllabus_text = ""

        if syllabus_file and syllabus_file.filename:
            syllabus_res = safe_ingest(
                file_source=syllabus_file.stream,
                filename=syllabus_file.filename,
                document_type="syllabus",
                subject=subject_name
            )
            syllabus_chunks = syllabus_res.get("chunks_created", 0)
            syllabus_file.stream.seek(0)
            syllabus_text = ingestion_service.extract_text(syllabus_file.stream, syllabus_file.filename)

            # Topic extraction is deliberately local during onboarding. A remote
            # Gemini parse here made a DNS/API retry block the whole upload.
            for line in syllabus_text.splitlines():
                line = line.strip()
                if not line or len(line) > 140:
                    continue
                candidate = re.sub(
                    r"^(?:module\s*\d+\s*[:.-]?|unit\s*\d+\s*[:.-]?|[-*•]|[0-9]+[.)])\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
                if ":" in candidate:
                    candidate = candidate.split(":", 1)[-1].strip()
                if 4 <= len(candidate) <= 100 and candidate not in detected_topics:
                    detected_topics.append(candidate)

        # 2. Ingest PYQs
        pyq_chunks = 0
        pyq_questions_list = []
        pyq_keys = ["pyq1", "pyq2", "pyq3"]
        for idx, k in enumerate(pyq_keys, 1):
            f = request.files.get(k)
            if f and f.filename:
                year_cand = str(2026 - idx)
                res = safe_ingest(
                    file_source=f.stream,
                    filename=f.filename,
                    document_type="pyq",
                    subject=subject_name,
                    year=year_cand
                )
                pyq_chunks += res.get("chunks_created", 0)
                f.stream.seek(0)
                ptext = ingestion_service.extract_text(f.stream, f.filename)

                lines = [l.strip() for l in ptext.splitlines() if l.strip()]
                for l in lines:
                    m = re.match(r"^(?:Q\d+|[0-9]+[a-z]?\.)\s+(.+?)(?:\[(\d+)\s*(?:marks|m)?\])?$", l, re.IGNORECASE)
                    if m:
                        q_str = m.group(1)
                        marks_val = int(m.group(2) or 5)
                        matched_top = "Core Concepts"
                        for dt in detected_topics:
                            if any(w.lower() in q_str.lower() for w in dt.split() if len(w) > 3):
                                matched_top = dt
                                break
                        pyq_questions_list.append({
                            "question": q_str,
                            "marks": marks_val,
                            "year": year_cand,
                            "topic": matched_top,
                            "difficulty": "Medium",
                            "question_type": "Descriptive"
                        })

        # 3. Ingest Notes
        notes_file = request.files.get("notes_file")
        notes_chunks = 0
        if notes_file and notes_file.filename:
            notes_res = safe_ingest(
                file_source=notes_file.stream,
                filename=notes_file.filename,
                document_type="notes",
                subject=subject_name
            )
            notes_chunks = notes_res.get("chunks_created", 0)

        if not detected_topics:
            detected_topics = [f"{subject_name} Core Concepts"]

        # Feed to pyq_service
        if pyq_questions_list:
            pyq_service.index_pyq_analyses(subject_name=subject_name, pyq_questions=pyq_questions_list)
        else:
            pyq_service.index_pyq_analyses(subject_name=subject_name, pyq_questions=[])

        # 4. Initialize Database records for student
        user = db.query(User).filter_by(id=student_id).first()
        if not user:
            user = User(id=student_id, username=f"student_{student_id}")
            db.add(user)
            db.flush()

        subj = db.query(Subject).filter_by(name=subject_name).first()
        if not subj:
            subj = Subject(name=subject_name)
            db.add(subj)
            db.flush()

        for top in detected_topics[:8]:
            existing_m = db.query(StudentTopicMastery).filter_by(student_id=student_id, subject_id=subj.id, topic_name=top).first()
            if not existing_m:
                new_m = StudentTopicMastery(
                    student_id=student_id,
                    subject_id=subj.id,
                    topic_name=top,
                    mastery_score=0.0,
                    confidence=0.0,
                    attempt_count=0,
                    correct_count=0
                )
                db.add(new_m)
            elif existing_m.attempt_count == 0 and existing_m.mastery_score == 45.0:
                # Replace the former placeholder baseline with an honest
                # zero until the student has attempted an assessment.
                existing_m.mastery_score = 0.0
                existing_m.confidence = 0.0
        db.commit()

        total_chunks = syllabus_chunks + pyq_chunks + notes_chunks
        return jsonify({
            "success": True,
            "data": {
                "subject": subject_name,
                "syllabus_extracted": True,
                "chunks_indexed": total_chunks,
                "pyq_questions_detected": len(pyq_questions_list),
                "concepts_identified": len(detected_topics),
                "recurring_topics_found": min(len(detected_topics), 5),
                "knowledge_graph_built": False,
                "rag_indexing": {
                    "status": "partial_success" if indexing_warnings else "success",
                    "warnings": indexing_warnings
                },
                "processing_seconds": round(time.perf_counter() - started_at, 2)
            }
        })

    except Exception as error:
        db.rollback()
        print(f"[Process Materials Error]: {error}")
        return jsonify({"success": False, "error": str(error)}), 500
    finally:
        db.close()


# -------------------------------------------------------------
# 11. Authentication Endpoints (Supabase Auth / GoTrue)
# -------------------------------------------------------------
@api_bp.route("/auth/signup", methods=["POST"])
def auth_signup():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    res = supabase_service.sign_up(email, password)
    if not res.get("success"):
        return jsonify({"success": False, "error": {"code": "SIGNUP_FAILED", "message": res.get("error", "Sign up failed")}}), 400

    user_info = res.get("user", {})
    session["user_id"] = user_info.get("id")
    session["user_email"] = user_info.get("email")

    return jsonify({"success": True, "data": res})


@api_bp.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    res = supabase_service.sign_in(email, password)
    if not res.get("success"):
        return jsonify({"success": False, "error": {"code": "LOGIN_FAILED", "message": res.get("error", "Invalid credentials")}}), 401

    user_info = res.get("user", {})
    session["user_id"] = user_info.get("id")
    session["user_email"] = user_info.get("email")

    return jsonify({"success": True, "data": res})


@api_bp.route("/auth/session", methods=["GET"])
def auth_session():
    user = get_authenticated_user()
    if user:
        return jsonify({"success": True, "data": {"authenticated": True, "user": user}})
    return jsonify({"success": True, "data": {"authenticated": False, "user": None}})


@api_bp.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True, "data": {"message": "Logged out successfully"}})


# -------------------------------------------------------------
# 12. Study Space Endpoints
# -------------------------------------------------------------
@api_bp.route("/study-sessions", methods=["GET"])
@require_auth
def list_study_spaces(user):
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    sessions = supabase_service.get_study_sessions(user_id, user_token=token)
    return jsonify({"success": True, "data": sessions})


@api_bp.route("/study-sessions", methods=["POST"])
@require_auth
def create_study_space(user):
    data = request.get_json() or {}
    name = data.get("name", "").strip() or "Untitled Study Session"
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    space = supabase_service.create_study_session(user_id, name, user_token=token)
    return jsonify({"success": True, "data": space})


@api_bp.route("/study-sessions/<session_id>", methods=["GET"])
@require_auth
def get_study_space_detail(user, session_id):
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    space = supabase_service.get_study_session(session_id, user_id, user_token=token)
    if not space:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Study space not found"}}), 404

    docs = supabase_service.get_session_documents(session_id, user_id, user_token=token)
    space["documents"] = docs
    return jsonify({"success": True, "data": space})


@api_bp.route("/study-sessions/<session_id>/documents", methods=["POST"])
@require_auth
def upload_study_space_documents(user, session_id):
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    # Validate session ownership
    space = supabase_service.get_study_session(session_id, user_id, user_token=token)
    if not space:
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Study space not found or unauthorized"}}), 404

    uploaded_files = request.files.getlist("files")
    if not uploaded_files or not any(f.filename for f in uploaded_files):
        return jsonify({"success": False, "error": {"code": "NO_FILES", "message": "Please upload at least 1 file."}}), 400

    # Build files data tuples (filename, bytes)
    files_data = []
    for f in uploaded_files:
        if f.filename:
            content = f.read()
            files_data.append((f.filename, content))

    subject_name = request.form.get("session_name") or space.get("name") or "General"

    # Ingest using universal ingestion manager
    result = ingestion_manager.ingest_session_files(
        session_id=session_id,
        user_id=user_id,
        files_data=files_data,
        subject_name=subject_name,
        user_token=token
    )

    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@api_bp.route("/study-sessions/<session_id>/documents", methods=["GET"])
@require_auth
def get_study_space_documents(user, session_id):
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    docs = supabase_service.get_session_documents(session_id, user_id, user_token=token)
    return jsonify({"success": True, "data": docs})


# -------------------------------------------------------------
# 13. Persistent Chat & Chat History Endpoints
# -------------------------------------------------------------
@api_bp.route("/chat", methods=["POST"])
@require_auth
def chat_query(user):
    data = request.get_json() or {}
    question = (data.get("question") or data.get("message") or "").strip()
    study_session_id = data.get("session_id") or data.get("study_session_id")
    chat_session_id = data.get("chat_session_id")
    subject = data.get("subject", "General").strip()

    if not question:
        return jsonify({"success": False, "error": {"code": "EMPTY_QUESTION", "message": "Please enter a question."}}), 400

    if not study_session_id:
        return jsonify({"success": False, "error": {"code": "SESSION_REQUIRED", "message": "Please select a study space."}}), 400

    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    # Validate study session ownership
    study_space = supabase_service.get_study_session(study_session_id, user_id, user_token=token)
    if not study_space:
        return jsonify({"success": False, "error": {"code": "SESSION_UNAUTHORIZED", "message": "Study space not found or unauthorized"}}), 404

    # Ensure or create chat conversation
    if not chat_session_id:
        title = generate_chat_title(question)
        new_chat = supabase_service.create_chat_session(user_id, study_session_id, title=title, user_token=token)
        chat_session_id = new_chat["id"]

    # 1. Save user message first (Order Requirement 30)
    supabase_service.save_chat_message(
        chat_session_id=chat_session_id,
        user_id=user_id,
        role="user",
        content=question,
        user_token=token
    )

    # 2. Execute RAG scoped strictly to authenticated user and study space
    try:
        rag_res = rag_pipeline.query(
            question=question,
            subject=study_space.get("name") or subject,
            user_id=user_id,
            session_id=study_session_id,
            top_k=int(data.get("top_k", 5)),
            use_reasoning=bool(data.get("use_reasoning", False))
        )
        answer = rag_res.get("answer", "")
        citations = rag_res.get("citations", [])

        # 3. Save assistant message with real citations
        supabase_service.save_chat_message(
            chat_session_id=chat_session_id,
            user_id=user_id,
            role="assistant",
            content=answer,
            citations=citations,
            user_token=token
        )

        return jsonify({
            "success": True,
            "data": {
                "chat_session_id": chat_session_id,
                "question": question,
                "answer": answer,
                "citations": citations,
                "evidence_found": rag_res.get("evidence_found", False),
                "sources_used": rag_res.get("sources_used", []),
                "retrieval_count": rag_res.get("retrieval_count", 0)
            }
        })
    except Exception as rag_err:
        err_msg = f"Unable to retrieve grounded answer: {str(rag_err)}"
        supabase_service.save_chat_message(
            chat_session_id=chat_session_id,
            user_id=user_id,
            role="assistant",
            content=err_msg,
            user_token=token
        )
        return jsonify({"success": False, "error": {"code": "RAG_ERROR", "message": err_msg}}), 500


@api_bp.route("/chat/history", methods=["GET"])
@require_auth
def get_chat_history(user):
    user_id = str(user["id"])
    study_session_id = request.args.get("study_session_id") or request.args.get("session_id")
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    chats = supabase_service.get_chat_sessions(user_id, study_session_id=study_session_id, user_token=token)
    return jsonify({"success": True, "data": chats})


@api_bp.route("/chat/sessions", methods=["POST"])
@require_auth
def start_chat_session(user):
    user_id = str(user["id"])
    data = request.get_json() or {}
    study_session_id = data.get("study_session_id") or data.get("session_id")
    title = data.get("title", "").strip() or "New Discussion"

    if not study_session_id:
        return jsonify({"success": False, "error": {"code": "SESSION_REQUIRED", "message": "study_session_id is required"}}), 400

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    chat = supabase_service.create_chat_session(user_id, study_session_id, title=title, user_token=token)
    return jsonify({"success": True, "data": chat})


@api_bp.route("/chat/sessions/<chat_id>/messages", methods=["GET"])
@require_auth
def get_chat_messages(user, chat_id):
    user_id = str(user["id"])
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else None

    # Verify session ownership
    chat = supabase_service.get_chat_session(chat_id, user_id, user_token=token)
    if not chat:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Chat conversation not found"}}), 404

    messages = supabase_service.get_chat_messages(chat_id, user_id, user_token=token)
    return jsonify({"success": True, "data": messages})


# -------------------------------------------------------------
# 14. RAG Diagnostics & Status Endpoints
# -------------------------------------------------------------
@api_bp.route("/rag/status", methods=["GET"])
def rag_status_endpoint():
    """Report Chroma Cloud, Gemini, and Supabase connectivity without leaking credentials."""
    from services.rag.embeddings import get_rag_status
    status = get_rag_status()
    status["gemini_configured"] = bool(os.getenv("GEMINI_API_KEY"))
    status["supabase_configured"] = supabase_service.is_configured
    status["supabase_url"] = supabase_service.url if supabase_service.is_configured else "not_configured (using SQLite fallback)"
    return jsonify({"success": True, "data": status})


@api_bp.route("/rag/debug", methods=["POST"])
@require_auth
def rag_debug_endpoint(user):
    data = request.get_json() or {}
    question = data.get("query", "").strip()
    session_id = data.get("session_id")
    subject = data.get("subject", "General")

    start_t = time.perf_counter()
    retrieval = rag_pipeline.retriever.retrieve(
        query=question,
        subject=subject,
        user_id=str(user["id"]),
        session_id=session_id,
        top_k=int(data.get("top_k", 5))
    )
    elapsed = round(time.perf_counter() - start_t, 3)

    return jsonify({
        "success": True,
        "data": {
            "query": question,
            "session_id": session_id,
            "user_id": str(user["id"]),
            "retrieval_count": len(retrieval.get("chunks", [])),
            "chunks": [
                {
                    "chunk_id": c.get("chunk_id"),
                    "score": c.get("rerank_score", c.get("distance")),
                    "source": c.get("metadata", {}).get("source_name")
                }
                for c in retrieval.get("chunks", [])
            ],
            "latency_seconds": elapsed
        }
    })
