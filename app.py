import os
import time
import uuid
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from dotenv import load_dotenv

from models.database import init_db
from routes.exam_routes import exam_bp
from routes.learning_routes import learning_bp
from routes.viva_routes import viva_bp
from routes.api_routes import api_bp
from services.gemini_service import ask_gemini
from services.tutor_service import answer_tutor_question
from services.rag.rag_pipeline import get_rag_pipeline
from services.rag.ingestion import UniversalIngestionService
from services.demo_service import seed_demo_data

load_dotenv()

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "system"
        return True

# Structured Logger
handler = logging.StreamHandler()
handler.addFilter(RequestIdFilter())
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [Req:%(request_id)s] %(message)s"))
logger = logging.getLogger("abhyas_ai")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Initialize database
try:
    init_db()
except Exception as db_err:
    print(f"Warning: Database initialization error: {db_err}")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "abhyas_ai_secret_key_2026")

# Register All Feature Blueprints
app.register_blueprint(exam_bp)
app.register_blueprint(learning_bp)
app.register_blueprint(viva_bp)
app.register_blueprint(api_bp)

# In-memory session fallback cache for transcripts
TRANSCRIPT_STORE = {}


@app.before_request
def before_request_logging():
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()


@app.after_request
def after_request_logging(response):
    req_id = getattr(g, "request_id", "internal")
    duration = time.time() - getattr(g, "start_time", time.time())
    logger.info(
        f"Path: {request.path} | Method: {request.method} | Status: {response.status_code} | Latency: {duration:.3f}s",
        extra={"request_id": req_id}
    )
    return response


# -------------------------------------------------------------
# Primary Navigation Views
# -------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/system-health")
def system_health():
    return render_template("system_health.html")


@app.route("/onboarding")
def onboarding():
    return render_template("onboarding.html")


@app.route("/answer-evaluator")
def answer_evaluator_view():
    return render_template("answer_evaluator.html")


@app.route("/answer-mode")
def answer_mode_view():
    return render_template("answer_mode.html")


@app.route("/viva-arena")
def viva_arena_view():
    return render_template("viva_arena.html")


@app.route("/demo")
def demo_route():
    try:
        seed_demo_data()
    except Exception as err:
        print(f"Demo seeding notice: {err}")
    return redirect("/dashboard")


@app.route("/learn")
def learn():
    return render_template("learning/learn.html")


# -------------------------------------------------------------
# YouTube Processing & AI Tutor Endpoints
# -------------------------------------------------------------
@app.route("/process-youtube", methods=["POST"])
def process_youtube():
    from services.youtube_service import extract_video_id
    from services.transcript_service import get_transcript
    from services.quiz_service import generate_quiz

    data = request.get_json() or {}
    youtube_url = data.get("url", "").strip()

    if not youtube_url:
        return jsonify({
            "success": False,
            "error": "Please enter a YouTube URL."
        }), 400

    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({
            "success": False,
            "error": "Invalid YouTube URL."
        }), 400

    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({
            "success": False,
            "error": "Could not retrieve the transcript for this video."
        }), 400

    # Save transcript in server cache and store current video_id in session
    TRANSCRIPT_STORE[video_id] = transcript
    session["video_id"] = video_id

    # Automatically index transcript into ChromaDB for universal RAG search
    try:
        ingestion = UniversalIngestionService()
        ingestion.ingest_youtube_transcript(
            video_id=video_id,
            transcript_text=transcript,
            subject=session.get("current_subject", "General")
        )
    except Exception as rag_ingest_err:
        print(f"[RAG] YouTube transcript background indexing warning: {rag_ingest_err}")

    # Generate Quiz
    try:
        quiz = generate_quiz(transcript)
    except Exception as error:
        print(f"Quiz generation error: {error}")
        return jsonify({
            "success": False,
            "error": "Something went wrong while generating the quiz."
        }), 500

    return jsonify({
        "success": True,
        "video_id": video_id,
        "quiz": quiz.model_dump()
    })


@app.route("/ask-tutor", methods=["POST"])
def ask_tutor():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    video_id = data.get("video_id") or session.get("video_id")

    if not question:
        return jsonify({
            "success": False,
            "error": "Please enter a question for the AI Tutor."
        }), 400

    if not video_id or video_id not in TRANSCRIPT_STORE:
        return jsonify({
            "success": False,
            "error": "No active lecture found! Please paste a YouTube lecture link first."
        }), 400

    transcript = TRANSCRIPT_STORE[video_id]

    try:
        # Ground through tutor service
        answer = answer_tutor_question(transcript, question)
        return jsonify({
            "success": True,
            "video_id": video_id,
            "answer": answer
        })
    except Exception as error:
        print(f"AI Tutor Error: {error}")
        return jsonify({
            "success": False,
            "error": "Something went wrong while consulting the AI Tutor."
        }), 500


@app.route("/test-gemini")
def test_gemini():
    answer = ask_gemini("Reply with exactly: ABHYAS AI GEMINI CONNECTED")
    return answer


if __name__ == "__main__":
    app.run(debug=True)