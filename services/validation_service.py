from typing import Dict, Any, List
from models.exam_models import PracticePaperSet, ExamBlueprint


def validate_paper_set(paper_set: PracticePaperSet, blueprint: ExamBlueprint) -> Dict[str, Any]:
    """
    Programmatically validate generated practice papers against blueprint constraints.
    Returns validation status and any detected errors.
    """
    errors: List[str] = []

    paper_1 = paper_set.paper_1
    paper_2 = paper_set.paper_2

    # Calculate actual marks sums
    p1_actual_marks = _calculate_paper_marks(paper_1)
    p2_actual_marks = _calculate_paper_marks(paper_2)

    # 1. Total marks validation
    if p1_actual_marks != blueprint.total_marks:
        errors.append(f"Paper 1 total marks ({p1_actual_marks}) does not match blueprint total marks ({blueprint.total_marks}).")

    if p2_actual_marks != blueprint.total_marks:
        errors.append(f"Paper 2 total marks ({p2_actual_marks}) does not match blueprint total marks ({blueprint.total_marks}).")

    # 2. Non-empty questions validation
    p1_questions = _get_all_questions(paper_1)
    p2_questions = _get_all_questions(paper_2)

    if not p1_questions:
        errors.append("Paper 1 contains no questions.")
    if not p2_questions:
        errors.append("Paper 2 contains no questions.")

    for q in p1_questions:
        if not q.question_text.strip():
            errors.append(f"Paper 1 question '{q.question_number}' has empty text.")

    for q in p2_questions:
        if not q.question_text.strip():
            errors.append(f"Paper 2 question '{q.question_number}' has empty text.")

    # 3. Distinctness check between Paper 1 and Paper 2
    p1_texts = {q.question_text.strip().lower() for q in p1_questions}
    p2_texts = {q.question_text.strip().lower() for q in p2_questions}
    overlapping_questions = p1_texts.intersection(p2_texts)

    if len(overlapping_questions) > len(p1_questions) * 0.4:
        errors.append("Paper 1 and Paper 2 have high duplicate question overlap.")

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "paper_1_actual_marks": p1_actual_marks,
        "paper_2_actual_marks": p2_actual_marks,
        "expected_marks": blueprint.total_marks
    }


def _calculate_paper_marks(paper) -> int:
    total = 0
    for section in paper.sections:
        for q in section.questions:
            # If question is an optional choice (OR alternative), it doesn't add to required total attempted marks
            if not getattr(q, 'is_optional_choice', False):
                total += q.marks
    return total


def _get_all_questions(paper):
    questions = []
    for section in paper.sections:
        questions.extend(section.questions)
    return questions
