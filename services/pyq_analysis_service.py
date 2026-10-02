from typing import List
from models.exam_models import Syllabus, PYQAnalysis
from services.gemini_service import call_gemini_with_retry


def analyze_pyqs(pyq_texts: List[str], syllabus: Syllabus) -> PYQAnalysis:
    """
    Analyze previous year question papers against the structured syllabus context
    to extract topics, question patterns, weightages, and difficulty levels.
    """
    if not pyq_texts:
        raise ValueError("At least one previous year paper text must be provided.")

    combined_pyqs = "\n\n=== NEXT QUESTION PAPER ===\n\n".join(pyq_texts)
    syllabus_summary = syllabus.model_dump_json(indent=2)

    prompt = f"""
You are an expert university examiner analyzing past year question papers (PYQs).

Your goal is to perform a detailed structural analysis of the past year papers using the provided Syllabus as reference.

Instructions:
1. Extract questions from the past papers.
2. For each question, map it to the exact Module and Topic from the provided Syllabus.
3. Identify question marks, question type (e.g. Short Answer, Descriptive, Numerical, Diagram-based), and difficulty (Easy, Medium, Hard).
4. Calculate estimated weightage (%) for each module based on marks assigned.
5. Identify recurring / frequently asked topics.
6. Identify key exam question patterns (e.g. "Explain with neat sketch", "Differentiate between X and Y", "Solve numerical on Z").
7. Extract the overall `pyq_paper_structure_pattern`: detailed breakdown of paper layout (e.g., "Q1: 2-mark short questions (10 marks), Q2: Module 1 internal choice 6-7 marks (Q2a OR Q2b), Q3: Module 2 choice 6-7 marks, Q4: Module 3 choice 6-7 marks", or End-Sem breakdown like "Q1 compulsory 20 marks, Q2-Q6 attempt 3 out of 5 of 20 marks each").

Syllabus Reference:
-------------------
{syllabus_summary}
-------------------

Past Year Question Papers (PYQs):
---------------------------------
{combined_pyqs}
---------------------------------
"""

    response_text = call_gemini_with_retry(
        prompt=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": PYQAnalysis.model_json_schema()
        }
    )

    pyq_analysis = PYQAnalysis.model_validate_json(response_text)
    return pyq_analysis
