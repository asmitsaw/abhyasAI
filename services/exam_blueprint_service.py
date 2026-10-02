from typing import List, Optional
from models.exam_models import Syllabus, PYQAnalysis, ExamBlueprint
from services.gemini_service import call_gemini_with_retry


def create_exam_blueprint(
    syllabus: Syllabus,
    pyq_analysis: PYQAnalysis,
    paper_type: str,
    total_marks: int,
    selected_modules: List[str],
    custom_instructions: Optional[str] = ""
) -> ExamBlueprint:
    """
    Construct an Exam Blueprint mapping out question specifications, target modules,
    marks per question, and difficulty levels based on Syllabus, PYQ analysis, and user constraints.
    """
    syllabus_summary = syllabus.model_dump_json(indent=2)
    pyq_summary = pyq_analysis.model_dump_json(indent=2)

    prompt = f"""
You are an examination controller creating an official EXAM BLUEPRINT for a university paper.

User Requirements:
- Paper Type: {paper_type}
- Total Marks: {total_marks}
- Selected Modules: {", ".join(selected_modules) if selected_modules else "All Modules"}
- Custom Instructions: {custom_instructions if custom_instructions else "None"}

Context Data:
Syllabus:
{syllabus_summary}

PYQ Analysis & Historical Patterns:
{pyq_summary}

FORMAT PATTERN MANDATES:
1. IF Paper Type is 'End Semester Exam' or PYQ pattern matching is requested:
   - Mirror the EXACT structural pattern (`pyq_paper_structure_pattern`) discovered in the PYQ Analysis.
   - Set `format_pattern` to "End Semester PYQ Pattern".

2. FOR Unit Test / Mid Sem / Standard Practice Papers:
   - Provide a compulsory 2-marks short question section (e.g., Q1 consisting of 2-mark conceptual questions).
   - Provide module-wise internal choice questions (Any 1 of 2 questions per module, worth 6-7 marks each). For example:
     - Question 1 (Module 1): 2 sub-question choices (6-7 marks each, `or_choice_group` = "Q1_MOD1_OR")
     - Question 2 (Module 2): 2 sub-question choices (6-7 marks each, `or_choice_group` = "Q2_MOD2_OR")
     - Question 3 (Module 3): 2 sub-question choices (6-7 marks each, `or_choice_group` = "Q3_MOD3_OR")
   - Set `format_pattern` to "Module Choice (6-7 Marks + 2 Marks Short Questions)".

3. Create a question specification list where questions cover ONLY the selected modules: {selected_modules}.
4. Allocate question weights based on historical topic importance from the PYQ analysis.
5. Create a realistic balance of Easy, Medium, and Hard difficulty questions.

Generate the blueprint adhering strictly to the schema.
"""

    response_text = call_gemini_with_retry(
        prompt=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ExamBlueprint.model_json_schema()
        }
    )

    blueprint = ExamBlueprint.model_validate_json(response_text)
    return blueprint
