import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///abhyas.db")

# For SQLite, handle same thread connection
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic_masteries = relationship("StudentTopicMastery", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    code = Column(String(50), nullable=True)
    syllabus_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    exam_date = Column(DateTime, nullable=True)
    total_marks = Column(Integer, default=100)
    target_score = Column(Float, default=85.0)


class StudentSubject(Base):
    __tablename__ = "student_subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    target_grade = Column(String(10), default="A")


class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    topic_name = Column(String(200), nullable=False, index=True)
    module_name = Column(String(200), default="", nullable=True)
    mastery_score = Column(Float, default=0.0)  # 0 to 100
    confidence = Column(Float, default=0.0)     # 0 to 1
    attempt_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, nullable=True)
    last_correct = Column(DateTime, nullable=True)
    average_response_time = Column(Float, default=0.0)
    difficulty_seen = Column(String(50), default="Medium")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("User", back_populates="topic_masteries")

    __table_args__ = (
        Index("idx_student_subject_topic", "student_id", "subject_id", "topic_name"),
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    video_id = Column(String(100), nullable=True)
    total_questions = Column(Integer, default=20)
    score = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    completed_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="quiz_attempts")
    questions = relationship("QuestionAttempt", back_populates="quiz_attempt", cascade="all, delete-orphan")


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_name = Column(String(200), nullable=False)
    question_text = Column(Text, nullable=False)
    selected_option = Column(String(500), nullable=False)
    correct_option = Column(String(500), nullable=False)
    is_correct = Column(Boolean, default=False)
    difficulty = Column(String(50), default="Medium")
    response_time_seconds = Column(Float, default=15.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    quiz_attempt = relationship("QuizAttempt", back_populates="questions")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    paper_title = Column(String(200), default="Practice Exam")
    score = Column(Float, default=0.0)
    total_marks = Column(Integer, default=100)
    time_spent_seconds = Column(Integer, default=0)
    topic_breakdown_json = Column(Text, default="{}")
    completed_at = Column(DateTime, default=datetime.utcnow)


class VivaAttempt(Base):
    __tablename__ = "viva_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    examiner_mode = Column(String(50), default="Professor")
    overall_score = Column(Float, default=0.0)
    total_questions = Column(Integer, default=5)
    feedback = Column(Text, nullable=True)
    report_json = Column(Text, default="{}")
    completed_at = Column(DateTime, default=datetime.utcnow)


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_name = Column(String(200), nullable=False)
    duration_minutes = Column(Integer, default=25)
    completed = Column(Boolean, default=False)
    session_type = Column(String(50), default="Practice")
    created_at = Column(DateTime, default=datetime.utcnow)


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    exam_date = Column(DateTime, nullable=True)
    available_minutes = Column(Integer, default=120)
    plan_json = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(100), nullable=False)  # QUIZ_ANSWER, VIVA_RESPONSE, EXAM_SUBMIT, STUDY_SESSION
    subject_name = Column(String(200), default="General")
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
