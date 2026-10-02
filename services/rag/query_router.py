import re
from enum import Enum
from typing import Dict, List, Optional


class QueryType(str, Enum):
    GENERAL_TUTOR = "GENERAL_TUTOR"
    SYLLABUS = "SYLLABUS"
    PYQ = "PYQ"
    EXAM_PATTERN = "EXAM_PATTERN"
    TOPIC = "TOPIC"
    LECTURE = "LECTURE"
    ANSWER_EVALUATION = "ANSWER_EVALUATION"
    VIVA = "VIVA"
    STUDY_PLAN = "STUDY_PLAN"
    CONCEPT = "CONCEPT"
    REVISION = "REVISION"


class QueryRouter:
    """
    Classifies user queries into semantic retrieval intents to choose
    the optimal ChromaDB collections, metadata filters, and retrieval weights.
    """

    def route_query(self, query: str) -> QueryType:
        q = query.lower().strip()

        # STUDY_PLAN / WHAT SHOULD I STUDY NOW
        if any(p in q for p in ["what should i study", "study plan", "how to prepare", "schedule", "timetable", "where do i start", "study next", "i'm cooked", "im cooked"]):
            return QueryType.STUDY_PLAN

        # VIVA
        if any(p in q for p in ["viva", "oral exam", "examiner", "ask me question", "quiz me orally", "interview"]):
            return QueryType.VIVA

        # ANSWER_EVALUATION
        if any(p in q for p in ["evaluate my answer", "grade this", "how should i answer", "for 10 marks", "for 5 marks", "for 2 marks", "marks answer"]):
            return QueryType.ANSWER_EVALUATION

        # EXAM_PATTERN
        if any(p in q for p in ["important", "weightage", "marks distribution", "repeated topic", "exam pattern", "blueprint", "frequently asked", "which module has highest marks"]):
            return QueryType.EXAM_PATTERN

        # PYQ
        if any(p in q for p in ["past paper", "pyq", "previous year", "asked in 20", "asked in 19", "previous exam", "question paper"]):
            return QueryType.PYQ

        # SYLLABUS
        if any(p in q for p in ["in the syllabus", "which module", "curriculum", "syllabus", "units covered", "course outcomes"]):
            return QueryType.SYLLABUS

        # LECTURE
        if any(p in q for p in ["in the lecture", "in the video", "did the teacher say", "prof mention", "timestamp", "video says"]):
            return QueryType.LECTURE

        # REVISION
        if any(p in q for p in ["rapid revision", "summary of", "cheat sheet", "recap", "formula sheet", "quick overview"]):
            return QueryType.REVISION

        # CONCEPT
        if any(p in q for p in ["difference between", "compare", "prerequisite", "how does", "working of", "architecture of"]):
            return QueryType.CONCEPT

        # TOPIC (default concept explanation)
        if any(p in q for p in ["explain", "what is", "define", "describe", "why does"]):
            return QueryType.TOPIC

        return QueryType.GENERAL_TUTOR

    def get_target_collections(self, query_type: QueryType) -> List[str]:
        """
        Map query type to primary ChromaDB collections to search.
        """
        mapping = {
            QueryType.GENERAL_TUTOR: ["notes", "lectures", "syllabus", "documents"],
            QueryType.SYLLABUS: ["syllabus"],
            QueryType.PYQ: ["pyqs", "questions"],
            QueryType.EXAM_PATTERN: ["pyqs", "syllabus"],
            QueryType.TOPIC: ["notes", "lectures", "syllabus", "documents"],
            QueryType.LECTURE: ["lectures"],
            QueryType.ANSWER_EVALUATION: ["pyqs", "notes", "answers"],
            QueryType.VIVA: ["notes", "lectures", "concepts"],
            QueryType.STUDY_PLAN: ["syllabus", "pyqs", "notes"],
            QueryType.CONCEPT: ["notes", "syllabus", "lectures"],
            QueryType.REVISION: ["notes", "syllabus"]
        }
        return mapping.get(query_type, ["documents", "notes", "lectures"])
