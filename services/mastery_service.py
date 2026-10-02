from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from models.database import StudentTopicMastery, SessionLocal, User, Subject


def get_mastery_band(score: float) -> str:
    """
    Map 0-100 numerical mastery score into interpretable bands.
    """
    if score >= 90:
        return "Mastered"
    elif score >= 75:
        return "Strong"
    elif score >= 60:
        return "Developing"
    elif score >= 40:
        return "Weak"
    else:
        return "Critical"


def get_mastery_color(band: str) -> str:
    """
    Comic / neobrutalist status color corresponding to mastery band.
    """
    mapping = {
        "Critical": "#ed2929",   # Red
        "Weak": "#ff9800",       # Orange
        "Developing": "#ffd91a", # Yellow
        "Strong": "#4caf50",     # Green
        "Mastered": "#1595df"    # Blue/Hero
    }
    return mapping.get(band, "#ffd91a")


class MasteryService:
    """
    Interpretable, deterministic student mastery engine.
    Calculates 0-100 score based on actual student interaction data:
    accuracy, difficulty seen, consistency streaks, response time, and recency.
    """

    DIFFICULTY_WEIGHTS = {
        "easy": 0.8,
        "medium": 1.0,
        "hard": 1.25
    }

    def record_interaction(
        self,
        student_id: int,
        subject_name: str,
        topic_name: str,
        is_correct: bool,
        difficulty: str = "Medium",
        response_time_seconds: float = 15.0,
        module_name: str = "",
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Record a question or topic attempt and update student topic mastery.
        """
        local_db = db or SessionLocal()
        try:
            # Find or create subject
            subject = local_db.query(Subject).filter(Subject.name == subject_name).first()
            subject_id = subject.id if subject else None

            record = local_db.query(StudentTopicMastery).filter(
                StudentTopicMastery.student_id == student_id,
                StudentTopicMastery.topic_name == topic_name
            ).first()

            now = datetime.utcnow()

            if not record:
                record = StudentTopicMastery(
                    student_id=student_id,
                    subject_id=subject_id,
                    topic_name=topic_name,
                    module_name=module_name,
                    mastery_score=0.0,
                    confidence=0.0,
                    attempt_count=0,
                    correct_count=0,
                    last_attempt=now,
                    last_correct=now if is_correct else None,
                    average_response_time=response_time_seconds,
                    difficulty_seen=difficulty
                )
                local_db.add(record)

            # Update counters
            record.attempt_count += 1
            if is_correct:
                record.correct_count += 1
                record.last_correct = now

            record.last_attempt = now
            record.difficulty_seen = difficulty

            # Exponential moving average for response time
            alpha = 0.3
            record.average_response_time = (alpha * response_time_seconds) + ((1 - alpha) * record.average_response_time)

            # --- Deterministic Mastery Calculation ---
            diff_weight = self.DIFFICULTY_WEIGHTS.get(difficulty.lower(), 1.0)
            accuracy = record.correct_count / max(1, record.attempt_count)

            # Base score: up to 60 points from accuracy
            base_score = accuracy * 60.0

            # Difficulty bonus: up to 20 points
            difficulty_bonus = min(20.0, (diff_weight * accuracy) * 16.0)

            # Consistency & volume confidence: up to 15 points
            # Diminishing returns with sqrt of attempts
            volume_bonus = min(15.0, (record.attempt_count ** 0.5) * 4.0 * accuracy)

            # Response time efficiency: optimal between 5s and 45s
            time_bonus = 0.0
            if is_correct and 5.0 <= response_time_seconds <= 30.0:
                time_bonus = 5.0
            elif is_correct and response_time_seconds <= 60.0:
                time_bonus = 2.5

            total_score = base_score + difficulty_bonus + volume_bonus + time_bonus

            # Recency penalty if wrong recently
            if not is_correct:
                total_score = max(0.0, total_score * 0.85)

            new_mastery = round(max(0.0, min(100.0, total_score)), 1)
            record.mastery_score = new_mastery
            record.confidence = round(min(1.0, record.attempt_count / 10.0), 2)
            record.updated_at = now

            local_db.commit()

            band = get_mastery_band(new_mastery)
            return {
                "topic_name": topic_name,
                "mastery_score": new_mastery,
                "mastery_band": band,
                "confidence": record.confidence,
                "attempt_count": record.attempt_count,
                "correct_count": record.correct_count,
                "is_correct": is_correct
            }
        finally:
            if db is None:
                local_db.close()

    def get_subject_mastery(
        self,
        student_id: int,
        subject_name: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Fetch topic-level and aggregate mastery for a subject.
        """
        local_db = db or SessionLocal()
        try:
            records = local_db.query(StudentTopicMastery).filter(
                StudentTopicMastery.student_id == student_id
            ).all()

            # Filter records matching subject or general
            topics_data = []
            for r in records:
                band = get_mastery_band(r.mastery_score)
                topics_data.append({
                    "topic_id": r.id,
                    "topic_name": r.topic_name,
                    "module_name": r.module_name or "General",
                    "mastery_score": r.mastery_score,
                    "mastery_band": band,
                    "color": get_mastery_color(band),
                    "confidence": r.confidence,
                    "attempt_count": r.attempt_count,
                    "correct_count": r.correct_count,
                    "last_attempt": r.last_attempt.isoformat() if r.last_attempt else None,
                    "average_response_time": round(r.average_response_time, 1)
                })

            if not topics_data:
                # Return empty baseline
                return {
                    "subject": subject_name,
                    "overall_mastery": 0.0,
                    "overall_band": "Critical",
                    "total_topics_tracked": 0,
                    "topics": []
                }

            overall = round(sum(t["mastery_score"] for t in topics_data) / len(topics_data), 1)
            overall_band = get_mastery_band(overall)

            # Sort topics by lowest mastery first (weakest first)
            topics_data.sort(key=lambda x: x["mastery_score"])

            return {
                "subject": subject_name,
                "overall_mastery": overall,
                "overall_band": overall_band,
                "total_topics_tracked": len(topics_data),
                "weakest_topic": topics_data[0]["topic_name"] if topics_data else None,
                "topics": topics_data
            }
        finally:
            if db is None:
                local_db.close()
