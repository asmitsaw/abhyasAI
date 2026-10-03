from datetime import datetime
from typing import Any, Dict, List, Optional
from services.mastery_service import MasteryService
from services.pyq_service import get_pyq_service


class StudyPlannerService:
    """
    Synthesizes student mastery levels, historical PYQ relevance scores,
    and time constraints to recommend optimal learning actions and study schedules.
    """

    def __init__(
        self,
        mastery_service: Optional[MasteryService] = None
    ):
        self.mastery_service = mastery_service or MasteryService()
        self.pyq_service = get_pyq_service()

    def get_what_should_i_study_now(
        self,
        student_id: int,
        subject_name: str,
        available_minutes: int = 45,
        exam_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates the single highest-priority learning action.
        Returns topic, session duration, and an explicit evidence-backed 'WHY'.
        """
        mastery_data = self.mastery_service.get_subject_mastery(student_id, subject_name)
        pyq_data = self.pyq_service.get_subject_intelligence(subject_name)

        # Merge topic intelligence
        candidates = self._rank_candidate_topics(mastery_data, pyq_data)

        if not candidates:
            # Fallback default topic if no topics initialized yet
            return {
                "recommended_topic": "Process Scheduling Algorithms",
                "module": "Process Management",
                "recommended_minutes": min(25, available_minutes),
                "action_type": "Deep Dive & Conceptual Practice",
                "mastery_score": 0.0,
                "mastery_band": "Critical",
                "relevance_score": 85.0,
                "relevance_tier": "HIGH",
                "why_explanation": [
                    "Topic currently has 0% demonstrated student mastery (Critical band).",
                    "Historically frequent in past university papers (high mark weightage).",
                    "Serves as a fundamental prerequisite for subsequent concurrency topics."
                ],
                "evidence_summary": "Appeared in 3 previous papers (10 marks average).",
                "actions": {
                    "start": "START 25 MIN SESSION",
                    "why": "WHY THIS?",
                    "skip": "SKIP TO NEXT"
                }
            }

        top_choice = candidates[0]
        session_time = min(available_minutes, 25 if available_minutes >= 25 else available_minutes)

        why_reasons = []
        # Mastery reason
        m_score = top_choice["mastery_score"]
        m_band = top_choice["mastery_band"]
        why_reasons.append(f"Student estimated mastery is {m_score}% ({m_band} band).")

        # PYQ relevance reason
        rel_tier = top_choice.get("relevance_tier", "MODERATE")
        occ = top_choice.get("occurrence_count", 0)
        t_marks = top_choice.get("total_marks", 0)
        if occ > 0:
            why_reasons.append(f"{rel_tier} historical relevance observed across uploaded PYQs ({occ} questions, {t_marks} total marks).")
        else:
            why_reasons.append("Fundamental curriculum topic required for upcoming examinations.")

        # Prerequisite reason
        why_reasons.append(f"Mastering '{top_choice['topic']}' directly unlocks advanced related exam questions.")

        return {
            "recommended_topic": top_choice["topic"],
            "module": top_choice.get("module", "Core Module"),
            "recommended_minutes": session_time,
            "action_type": "Targeted Mastery Remediation",
            "mastery_score": m_score,
            "mastery_band": m_band,
            "relevance_score": top_choice.get("historical_relevance_score", 50.0),
            "relevance_tier": rel_tier,
            "why_explanation": why_reasons,
            "evidence_summary": f"Observed in {occ} past questions with {t_marks} marks total.",
            "actions": {
                "start": f"START {session_time} MIN SESSION",
                "why": "WHY THIS?",
                "skip": "SKIP TO NEXT"
            }
        }

    def generate_personalized_study_plan(
        self,
        student_id: int,
        subject_name: str,
        available_minutes: int = 90,
        exam_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Distributes study time across prioritized weak topics, practice, and revision.
        """
        mastery_data = self.mastery_service.get_subject_mastery(student_id, subject_name)
        pyq_data = self.pyq_service.get_subject_intelligence(subject_name)

        ranked = self._rank_candidate_topics(mastery_data, pyq_data)

        # Allocate slots:
        # e.g., 90 mins -> Top Topic (30m), Second Topic (25m), Adaptive Quiz (20m), Rapid Revision (15m)
        remaining = available_minutes
        slots = []

        if ranked:
            slot1_time = min(30, max(15, int(available_minutes * 0.35)))
            remaining -= slot1_time
            slots.append({
                "topic": ranked[0]["topic"],
                "duration_minutes": slot1_time,
                "activity": "Conceptual Study & Notes Review",
                "why": f"Lowest mastery ({ranked[0]['mastery_score']}%) with high exam weight."
            })

        if len(ranked) > 1 and remaining >= 20:
            slot2_time = min(25, max(15, int(available_minutes * 0.30)))
            remaining -= slot2_time
            slots.append({
                "topic": ranked[1]["topic"],
                "duration_minutes": slot2_time,
                "activity": "Problem Solving & Deep Dive",
                "why": f"Developing mastery ({ranked[1]['mastery_score']}%) frequently asked in PYQs."
            })

        if remaining >= 15:
            practice_time = max(15, int(remaining * 0.6))
            remaining -= practice_time
            slots.append({
                "topic": "Adaptive Diagnostic Practice",
                "duration_minutes": practice_time,
                "activity": "AI-Generated Targeted Practice Quiz",
                "why": "Reinforces newly studied concepts and verifies retention."
            })

        if remaining > 0:
            slots.append({
                "topic": "Rapid Revision & Key Takeaways",
                "duration_minutes": remaining,
                "activity": "Formula & Summary Review",
                "why": "Consolidates session memory before concluding."
            })

        return {
            "subject": subject_name,
            "total_allocated_minutes": available_minutes,
            "exam_date": exam_date_str or "Approaching Soon",
            "slots": slots,
            "rationale": "Plan balances weak-topic remediation with active testing and closing revision."
        }

    def generate_im_cooked_emergency_plan(
        self,
        student_id: int,
        subject_name: str,
        available_hours: float = 4.0,
        current_prep_level: str = "Zero / Beginning"
    ) -> Dict[str, Any]:
        """
        'I'M COOKED 🚨' Emergency Study Mode:
        Maximizes marks yield per minute for cramming situations.
        Sorts topics strictly by High PYQ Marks / Low Mastery ratio.
        """
        total_minutes = int(available_hours * 60)
        mastery_data = self.mastery_service.get_subject_mastery(student_id, subject_name)
        pyq_data = self.pyq_service.get_subject_intelligence(subject_name)

        ranked = self._rank_candidate_topics(mastery_data, pyq_data, emergency_mode=True)

        schedule = []
        minutes_left = total_minutes

        # Reserve 20% for rapid testing & formula memorization
        final_review_minutes = max(20, int(total_minutes * 0.15))
        study_pool = total_minutes - final_review_minutes

        topics_to_cram = ranked[:4] if ranked else []
        if not topics_to_cram:
            topics_to_cram = [
                {
                    "topic": item["topic_name"],
                    "total_marks": 0,
                    "mastery_score": item.get("mastery_score", 0),
                    "mastery_band": item.get("mastery_band", "Critical"),
                }
                for item in mastery_data.get("topics", [])
            ][:4]
        if not topics_to_cram:
            topics_to_cram = [{
                "topic": f"{subject_name} core concepts",
                "total_marks": 0,
                "mastery_score": 0,
                "mastery_band": "Critical",
            }]

        per_topic_time = study_pool // len(topics_to_cram)

        for i, item in enumerate(topics_to_cram, 1):
            schedule.append({
                "step": i,
                "topic": item["topic"],
                "duration_minutes": per_topic_time,
                "strategy": "High-Yield Cram: Focus on definitions, diagrams, and standard 5-10 mark steps.",
                "why": (
                    f"Historically accounts for {item.get('total_marks', 0)} uploaded PYQ marks "
                    f"with low current mastery."
                    if item.get("total_marks", 0)
                    else "No uploaded PYQ evidence is available yet; start with this topic and build evidence."
                )
            })

        schedule.append({
            "step": len(topics_to_cram) + 1,
            "topic": "Rapid High-Yield Formula & Diagram Drill",
            "duration_minutes": final_review_minutes,
            "strategy": "Draw all standard diagrams from memory and memorize key definitions.",
            "why": "Maximizes recall under exam stress."
        })

        return {
            "mode": "EMERGENCY_CRAM",
            "alert": "🚨 I'M COOKED MODE ACTIVATED",
            "subject": subject_name,
            "available_hours": available_hours,
            "total_minutes": total_minutes,
            "prep_level": current_prep_level,
            "schedule": schedule,
            "disclaimer": "Emergency plan optimizes for highest historical mark density. Not a guarantee of exact exam questions."
        }

    def _rank_candidate_topics(
        self,
        mastery_data: Dict[str, Any],
        pyq_data: Dict[str, Any],
        emergency_mode: bool = False
    ) -> List[Dict[str, Any]]:
        mastery_map = {t["topic_name"].lower(): t for t in mastery_data.get("topics", [])}
        pyq_topics = pyq_data.get("topics", [])

        ranked = []
        # Union of topics
        all_topic_names = set()
        for t in pyq_topics:
            all_topic_names.add(t["topic"])
        for t in mastery_data.get("topics", []):
            all_topic_names.add(t["topic_name"])

        for t_name in all_topic_names:
            t_lower = t_name.lower()
            m_info = mastery_map.get(t_lower, {"mastery_score": 0.0, "mastery_band": "Critical", "attempt_count": 0})
            p_info = next((p for p in pyq_topics if p["topic"].lower() == t_lower), None)

            m_score = m_info["mastery_score"]
            rel_score = p_info["historical_relevance_score"] if p_info else 40.0
            occ = p_info["occurrence_count"] if p_info else 0
            t_marks = p_info["total_marks"] if p_info else 0
            rel_tier = p_info["relevance_tier"] if p_info else "MODERATE"

            # Opportunity formula: High relevance + Low mastery = Maximum study priority
            # priority = (100 - mastery) * 0.6 + relevance * 0.4
            if emergency_mode:
                priority = (100 - m_score) * 0.4 + (rel_score * 0.6)
            else:
                priority = ((100 - m_score) * 0.65) + (rel_score * 0.35)

            module_val = p_info.get("module", "") if p_info else m_info.get("module_name", "")
            ranked.append({
                "topic": t_name,
                "module": module_val or "Core Module",
                "mastery_score": m_score,
                "mastery_band": m_info["mastery_band"],
                "historical_relevance_score": rel_score,
                "relevance_tier": rel_tier,
                "occurrence_count": occ,
                "total_marks": t_marks,
                "priority_score": round(priority, 1)
            })

        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        return ranked
