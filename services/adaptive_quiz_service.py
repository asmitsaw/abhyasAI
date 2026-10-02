import uuid
from typing import Any, Dict, List, Optional
from services.mastery_service import MasteryService
from services.llm.provider_factory import get_llm_provider


class AdaptiveQuizService:
    """
    Progressive adaptive testing engine:
    Dynamically adjusts question difficulty and concept focus based on student answer correctness.
    - Correct: Escalates difficulty (Easy -> Medium -> Hard).
    - Incorrect: Drops to prerequisite reinforcement or fundamental concept with remediation.
    """

    def __init__(
        self,
        mastery_service: Optional[MasteryService] = None,
        provider: Optional[Any] = None
    ):
        self.mastery_service = mastery_service or MasteryService()
        self.provider = provider or get_llm_provider()
        # In-memory active adaptive sessions
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def start_adaptive_quiz(
        self,
        student_id: int,
        subject_name: str,
        topic_name: Optional[str] = None,
        total_questions: int = 10
    ) -> Dict[str, Any]:
        session_id = f"adp_{uuid.uuid4().hex[:12]}"
        initial_difficulty = "Medium"
        active_topic = topic_name or "CPU Scheduling"

        # Generate initial question
        first_q = self._generate_adaptive_question(
            subject=subject_name,
            topic=active_topic,
            difficulty=initial_difficulty,
            q_num=1
        )

        session_state = {
            "session_id": session_id,
            "student_id": student_id,
            "subject_name": subject_name,
            "current_topic": active_topic,
            "current_difficulty": initial_difficulty,
            "question_index": 1,
            "total_questions": total_questions,
            "score": 0,
            "streak": 0,
            "history": [],
            "current_question": first_q
        }
        self._active_sessions[session_id] = session_state

        return {
            "session_id": session_id,
            "question_number": 1,
            "total_questions": total_questions,
            "subject": subject_name,
            "topic": active_topic,
            "difficulty": initial_difficulty,
            "question": first_q["question"],
            "options": first_q["options"]
        }

    def process_answer(
        self,
        session_id: str,
        selected_option: str,
        response_time_seconds: float = 15.0
    ) -> Dict[str, Any]:
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Adaptive session '{session_id}' not found or expired.")

        current_q = session["current_question"]
        correct_ans = current_q["correct_answer"].strip().lower()
        user_ans = selected_option.strip().lower()

        # Check correctness
        is_correct = (user_ans == correct_ans) or (user_ans in correct_ans) or (correct_ans in user_ans)

        if is_correct:
            session["score"] += 1
            session["streak"] += 1
        else:
            session["streak"] = 0

        # Update mastery in database
        mastery_result = self.mastery_service.record_interaction(
            student_id=session["student_id"],
            subject_name=session["subject_name"],
            topic_name=session["current_topic"],
            is_correct=is_correct,
            difficulty=session["current_difficulty"],
            response_time_seconds=response_time_seconds
        )

        # Determine next difficulty and topic adaptation
        if is_correct:
            if session["current_difficulty"] == "Easy":
                next_diff = "Medium"
            elif session["current_difficulty"] == "Medium":
                next_diff = "Hard"
            else:
                next_diff = "Hard"
            adaptation_note = "Great job! Difficulty increased for the next question."
        else:
            if session["current_difficulty"] == "Hard":
                next_diff = "Medium"
            else:
                next_diff = "Easy"
            adaptation_note = "Reviewing fundamental concepts with a targeted reinforcement question."

        session["current_difficulty"] = next_diff
        session["history"].append({
            "q_num": session["question_index"],
            "topic": session["current_topic"],
            "is_correct": is_correct,
            "difficulty": session["current_difficulty"]
        })

        is_finished = session["question_index"] >= session["total_questions"]

        if is_finished:
            final_report = {
                "session_id": session_id,
                "is_finished": True,
                "is_correct": is_correct,
                "correct_answer": current_q["correct_answer"],
                "explanation": current_q["explanation"],
                "mastery_update": mastery_result,
                "final_score": session["score"],
                "total_questions": session["total_questions"],
                "percentage": round((session["score"] / session["total_questions"]) * 100, 1),
                "adaptation_note": "Adaptive Quiz completed! Performance has updated your topic mastery."
            }
            # Clean up session
            del self._active_sessions[session_id]
            return final_report

        # Generate next adapted question
        session["question_index"] += 1
        next_q = self._generate_adaptive_question(
            subject=session["subject_name"],
            topic=session["current_topic"],
            difficulty=next_diff,
            q_num=session["question_index"]
        )
        session["current_question"] = next_q

        return {
            "session_id": session_id,
            "is_finished": False,
            "is_correct": is_correct,
            "correct_answer": current_q["correct_answer"],
            "explanation": current_q["explanation"],
            "mastery_update": mastery_result,
            "adaptation_note": adaptation_note,
            "next_question": {
                "question_number": session["question_index"],
                "total_questions": session["total_questions"],
                "topic": session["current_topic"],
                "difficulty": next_diff,
                "question": next_q["question"],
                "options": next_q["options"]
            }
        }

    def _generate_adaptive_question(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        q_num: int
    ) -> Dict[str, Any]:
        """
        Generate a single targeted MCQ via LLM provider.
        """
        prompt = (
            f"Subject: {subject}\n"
            f"Target Topic: {topic}\n"
            f"Target Difficulty: {difficulty}\n"
            f"Generate exactly 1 high-yield multiple choice question with 4 distinct options.\n"
            f"Include the single correct answer and a brief student-friendly explanation.\n"
            f"Output as JSON with keys: 'question', 'options' (list of 4 strings), 'correct_answer', 'explanation'."
        )
        schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
                "correct_answer": {"type": "string"},
                "explanation": {"type": "string"}
            },
            "required": ["question", "options", "correct_answer", "explanation"]
        }

        try:
            import json
            res = self.provider.generate_json(prompt=prompt, schema=schema)
            data = json.loads(res)
            if len(data.get("options", [])) == 4:
                return data
        except Exception as error:
            print(f"Adaptive question generation fallback: {error}")

        # Deterministic academic question fallback
        return {
            "question": f"In {subject} ({topic}), what is the primary operational objective?",
            "options": [
                "A. Maximize resource utilization and minimize latency",
                "B. Increase total instruction memory consumption",
                "C. Disable preemptive scheduling interrupts",
                "D. Eliminate cache memory hierarchy"
            ],
            "correct_answer": "A. Maximize resource utilization and minimize latency",
            "explanation": "Operating systems aim to optimize hardware utilization while providing low response latency."
        }
