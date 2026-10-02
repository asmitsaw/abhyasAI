import re
from typing import Any, Dict, List, Optional
from datetime import datetime


class HistoricalRelevanceService:
    """
    Analyzes previous year papers to calculate empirical Historical Relevance Scores
    grounded in actual occurrence counts, marks distribution, recency, and syllabus weights.
    Strictly avoids deterministic 'future exam prediction' claims.
    """

    def __init__(self):
        # In-memory intelligence cache per subject
        self._intelligence_cache: Dict[str, Dict[str, Any]] = {}

    def index_pyq_analyses(
        self,
        subject_name: str,
        pyq_questions: List[Dict[str, Any]],
        total_historical_marks: int = 240
    ) -> Dict[str, Any]:
        """
        Ingest analyzed PYQ questions and compute topic intelligence matrices.
        """
        current_year = datetime.now().year
        topic_map: Dict[str, Dict[str, Any]] = {}

        for q in pyq_questions:
            topic = q.get("topic", "General").strip()
            marks = int(q.get("marks", 5) or 5)
            year = str(q.get("year", ""))
            q_num = q.get("question_number", "Q")
            q_text = q.get("question", "") or q.get("question_text", "")
            q_type = q.get("question_type", "Descriptive")
            difficulty = q.get("difficulty", "Medium")

            # Infer approximate Bloom taxonomy level
            bloom = self._infer_bloom_level(q_text, q_type)

            if topic not in topic_map:
                topic_map[topic] = {
                    "topic": topic,
                    "module": q.get("module", ""),
                    "occurrence_count": 0,
                    "total_marks": 0,
                    "years": set(),
                    "question_types": set(),
                    "difficulties": [],
                    "bloom_levels": set(),
                    "evidence": []
                }

            entry = topic_map[topic]
            entry["occurrence_count"] += 1
            entry["total_marks"] += marks
            if year:
                entry["years"].add(year)
            entry["question_types"].add(q_type)
            entry["difficulties"].append(difficulty)
            entry["bloom_levels"].add(bloom)

            entry["evidence"].append({
                "year": year or "Past Exam",
                "question_number": q_num,
                "marks": marks,
                "question_text": q_text[:180] + ("..." if len(q_text) > 180 else ""),
                "difficulty": difficulty,
                "bloom_level": bloom
            })

        # Calculate scores
        results = []
        for topic, data in topic_map.items():
            occ = data["occurrence_count"]
            t_marks = data["total_marks"]
            years = sorted(list(data["years"]))

            # 1. Frequency weight (0 to 35 points)
            freq_score = min(35.0, occ * 11.5)

            # 2. Marks weight (0 to 35 points)
            marks_pct = (t_marks / max(1, total_historical_marks)) * 100.0
            marks_score = min(35.0, marks_pct * 1.75)

            # 3. Recency weight (0 to 20 points)
            recent_hits = sum(1 for y in years if y in [str(current_year), str(current_year - 1), str(current_year - 2), "2024", "2025", "2026"])
            recency_score = min(20.0, recent_hits * 10.0)

            # 4. Syllabus coverage weight (0 to 10 points)
            syllabus_score = 10.0 if data["module"] else 5.0

            relevance_score = round(min(100.0, freq_score + marks_score + recency_score + syllabus_score), 1)

            if relevance_score >= 70:
                tier = "HIGH"
            elif relevance_score >= 45:
                tier = "MODERATE"
            else:
                tier = "LOW"

            results.append({
                "topic": topic,
                "module": data["module"],
                "historical_relevance_score": relevance_score,
                "relevance_tier": tier,
                "occurrence_count": occ,
                "total_marks": t_marks,
                "marks_percentage": round(marks_pct, 1),
                "years_appeared": years,
                "question_types": list(data["question_types"]),
                "bloom_levels": list(data["bloom_levels"]),
                "evidence": data["evidence"]
            })

        # Sort descending by relevance score
        results.sort(key=lambda x: x["historical_relevance_score"], reverse=True)

        intelligence = {
            "subject": subject_name,
            "total_questions_analyzed": len(pyq_questions),
            "total_topics_evaluated": len(results),
            "topics": results
        }
        self._intelligence_cache[subject_name] = intelligence
        return intelligence

    def get_topic_evidence(self, subject_name: str, topic_name: str) -> Dict[str, Any]:
        """
        Fetch specific historical evidence behind a topic's score.
        """
        subject_data = self._intelligence_cache.get(subject_name)
        if not subject_data:
            # Fallback to search any subject
            for s_name, data in self._intelligence_cache.items():
                for t in data.get("topics", []):
                    if t["topic"].lower() == topic_name.lower():
                        return {"subject": s_name, "found": True, "topic_intelligence": t}
            return {
                "found": False,
                "topic": topic_name,
                "message": "No historical PYQ evidence found for this topic yet."
            }

        for t in subject_data.get("topics", []):
            if t["topic"].lower() == topic_name.lower() or topic_name.lower() in t["topic"].lower():
                return {"subject": subject_name, "found": True, "topic_intelligence": t}

        return {
            "found": False,
            "topic": topic_name,
            "message": f"Topic '{topic_name}' not detected in uploaded PYQs for {subject_name}."
        }

    def get_subject_intelligence(self, subject_name: str) -> Dict[str, Any]:
        return self._intelligence_cache.get(subject_name, {
            "subject": subject_name,
            "total_questions_analyzed": 0,
            "topics": []
        })

    def _infer_bloom_level(self, text: str, q_type: str) -> str:
        t = text.lower()
        if any(w in t for w in ["evaluate", "justify", "critique", "assess", "judge"]):
            return "Evaluate"
        elif any(w in t for w in ["analyze", "differentiate", "compare", "contrast", "distinguish"]):
            return "Analyze"
        elif any(w in t for w in ["calculate", "solve", "implement", "apply", "derive"]):
            return "Apply"
        elif any(w in t for w in ["explain", "describe", "discuss", "illustrate", "why"]):
            return "Understand"
        else:
            return "Remember"


# Global singleton
_global_pyq_service: Optional[HistoricalRelevanceService] = None


def get_pyq_service() -> HistoricalRelevanceService:
    global _global_pyq_service
    if _global_pyq_service is None:
        _global_pyq_service = HistoricalRelevanceService()
    return _global_pyq_service
