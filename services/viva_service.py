import uuid
import json
from typing import Any, Dict, List, Optional
from services.llm.provider_factory import get_llm_provider
from services.mastery_service import MasteryService


class VivaService:
    """
    Oral Examination / Viva Voce state engine:
    Features adaptive examiner personas (Professor, Strict Examiner, Friendly Mentor),
    dynamic follow-up questioning based on previous student response, and a final report.
    """

    EXAMINER_PERSONAS = {
        "Professor": "You are a scholarly university professor. You ask rigorous, conceptual questions, demand clarity on mechanisms and trade-offs, and maintain a dignified, formal academic tone.",
        "Strict Examiner": "You are a demanding, no-nonsense external university examiner. You look for technical imprecision, challenge vague claims, probe edge cases, and test whether the student actually understands or just memorized.",
        "Friendly Mentor": "You are a warm, encouraging senior study mentor. You guide the student through questions, celebrate good points, and ask gentle follow-up questions to help them uncover the right answers."
    }

    def __init__(
        self,
        mastery_service: Optional[MasteryService] = None,
        provider: Optional[Any] = None
    ):
        self.provider = provider or get_llm_provider()
        self.mastery_service = mastery_service or MasteryService()
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def start_viva(
        self,
        student_id: int,
        subject: str,
        topic: str = "General",
        examiner_mode: str = "Professor",
        max_questions: int = 4
    ) -> Dict[str, Any]:
        session_id = f"viva_{uuid.uuid4().hex[:12]}"
        persona_desc = self.EXAMINER_PERSONAS.get(examiner_mode, self.EXAMINER_PERSONAS["Professor"])

        # Generate first viva question
        first_q = self._generate_initial_viva_question(subject, topic, persona_desc)

        session_state = {
            "session_id": session_id,
            "student_id": student_id,
            "subject": subject,
            "topic": topic,
            "examiner_mode": examiner_mode,
            "persona_desc": persona_desc,
            "max_questions": max_questions,
            "current_index": 1,
            "dialogue": [
                {"role": "examiner", "question": first_q, "q_num": 1}
            ],
            "scores": []
        }
        self._sessions[session_id] = session_state

        return {
            "session_id": session_id,
            "examiner_mode": examiner_mode,
            "subject": subject,
            "topic": topic,
            "question_number": 1,
            "total_questions": max_questions,
            "question": first_q
        }

    def process_answer(
        self,
        session_id: str,
        student_answer: str
    ) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Viva session '{session_id}' not found or expired.")

        last_exchange = session["dialogue"][-1]
        examiner_question = last_exchange["question"]

        # 1. Analyze student answer
        analysis = self._analyze_viva_response(
            subject=session["subject"],
            topic=session["topic"],
            question=examiner_question,
            answer=student_answer,
            persona_desc=session["persona_desc"]
        )

        last_exchange["student_answer"] = student_answer
        last_exchange["analysis"] = analysis
        session["scores"].append(analysis.get("score_out_of_10", 7.0))

        # Record topic interaction for mastery
        is_good = analysis.get("score_out_of_10", 7.0) >= 6.0
        self.mastery_service.record_interaction(
            student_id=session["student_id"],
            subject_name=session["subject"],
            topic_name=session["topic"],
            is_correct=is_good,
            difficulty="Hard",
            response_time_seconds=30.0
        )

        is_finished = session["current_index"] >= session["max_questions"]

        if is_finished:
            # Generate final viva report
            final_report = self._generate_final_report(session)
            del self._sessions[session_id]
            return {
                "session_id": session_id,
                "is_finished": True,
                "current_feedback": analysis.get("examiner_comment", "Thank you."),
                "score_for_answer": analysis.get("score_out_of_10", 7.0),
                "final_report": final_report
            }

        # Generate adaptive follow-up question based on identified weakness or depth
        session["current_index"] += 1
        follow_up_q = self._generate_follow_up_question(session, analysis)
        session["dialogue"].append({
            "role": "examiner",
            "question": follow_up_q,
            "q_num": session["current_index"]
        })

        return {
            "session_id": session_id,
            "is_finished": False,
            "examiner_comment": analysis.get("examiner_comment", "Good point."),
            "score_for_answer": analysis.get("score_out_of_10", 7.0),
            "next_question": {
                "question_number": session["current_index"],
                "total_questions": session["max_questions"],
                "question": follow_up_q
            }
        }

    def _generate_initial_viva_question(self, subject: str, topic: str, persona_desc: str) -> str:
        prompt = (
            f"{persona_desc}\n"
            f"You are conducting a viva voce oral examination for a university student in {subject}.\n"
            f"Topic: {topic}\n"
            f"Ask an engaging, thought-provoking opening question that tests their conceptual understanding of this topic.\n"
            f"Keep your question concise, spoken-style, and directly to the point. Do not add conversational fluff before or after."
        )
        return self.provider.generate(prompt=prompt, temperature=0.5).strip()

    def _analyze_viva_response(
        self,
        subject: str,
        topic: str,
        question: str,
        answer: str,
        persona_desc: str
    ) -> Dict[str, Any]:
        prompt = (
            f"{persona_desc}\n"
            f"Evaluate this viva voce oral response.\n"
            f"Question: {question}\n"
            f"Student's Oral Answer: {answer}\n\n"
            f"Evaluate:\n"
            f"1. Score (out of 10).\n"
            f"2. Conceptual accuracy and completeness.\n"
            f"3. Specific weakness or missing nuance in their answer.\n"
            f"4. A brief, spoken-style comment from you as the examiner.\n"
            f"Output strictly valid JSON with keys: 'score_out_of_10', 'accuracy_summary', 'identified_weakness', 'examiner_comment'."
        )
        schema = {
            "type": "object",
            "properties": {
                "score_out_of_10": {"type": "number"},
                "accuracy_summary": {"type": "string"},
                "identified_weakness": {"type": "string"},
                "examiner_comment": {"type": "string"}
            },
            "required": ["score_out_of_10", "accuracy_summary", "identified_weakness", "examiner_comment"]
        }

        try:
            res = self.provider.generate_json(prompt=prompt, schema=schema)
            return json.loads(res)
        except Exception:
            return {
                "score_out_of_10": 7.0,
                "accuracy_summary": "Response shows reasonable understanding.",
                "identified_weakness": "Could provide more concrete algorithmic depth.",
                "examiner_comment": "Alright. Let us dive a bit deeper into this mechanism."
            }

    def _generate_follow_up_question(self, session: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        weakness = analysis.get("identified_weakness", "")
        last_q = session["dialogue"][-1]["question"]
        last_a = session["dialogue"][-1].get("student_answer", "")

        prompt = (
            f"{session['persona_desc']}\n"
            f"You are conducting a viva voce for {session['subject']} on '{session['topic']}'.\n"
            f"Previous Question: {last_q}\n"
            f"Student Answer: {last_a}\n"
            f"Weakness/Nuance to probe: {weakness}\n"
            f"Now formulate your follow-up question. It MUST build directly on what the student said or challenge their weakness.\n"
            f"Keep it concise, direct, and conversational."
        )
        return self.provider.generate(prompt=prompt, temperature=0.6).strip()

    def _generate_final_report(self, session: Dict[str, Any]) -> Dict[str, Any]:
        avg_score = round(sum(session["scores"]) / max(1, len(session["scores"])), 1)
        performance_tier = "Distinction" if avg_score >= 8.5 else ("First Class" if avg_score >= 7.0 else "Pass")

        exchanges = []
        for item in session["dialogue"]:
            exchanges.append({
                "question": item["question"],
                "student_answer": item.get("student_answer", ""),
                "score": item.get("analysis", {}).get("score_out_of_10", 0)
            })

        return {
            "subject": session["subject"],
            "topic": session["topic"],
            "examiner_mode": session["examiner_mode"],
            "total_questions": session["max_questions"],
            "average_score": avg_score,
            "max_score": 10.0,
            "performance_tier": performance_tier,
            "examiner_summary": f"The student completed oral examination with {session['examiner_mode']}. Demonstrated {performance_tier.lower()} level comprehension.",
            "dialogue_history": exchanges,
            "recommended_focus": f"Review edge cases and formal definitions for '{session['topic']}'."
        }


_global_viva_service: Optional[VivaService] = None


def get_viva_service() -> VivaService:
    global _global_viva_service
    if _global_viva_service is None:
        _global_viva_service = VivaService()
    return _global_viva_service
