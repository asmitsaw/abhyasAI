from typing import List, Dict, Any
from services.document_service import extract_and_clean_document
from services.syllabus_service import parse_syllabus
from services.pyq_analysis_service import analyze_pyqs
from services.exam_blueprint_service import create_exam_blueprint
from services.paper_generation_service import generate_practice_papers
from services.validation_service import validate_paper_set


def run_exam_prep_pipeline(
    pyq_files: List[tuple],  # List of (file_source, filename)
    syllabus_file_or_text: tuple,  # (file_source_or_text, filename_or_none)
    paper_type: str = "Unit Test",
    total_marks: int = 20,
    selected_module_names: List[str] = None,
    custom_instructions: str = ""
) -> Dict[str, Any]:
    """
    Complete end-to-end pipeline for Abhyas Exam Prep:
    1. Ingestion: Extract text from 3 PYQs and Syllabus.
    2. Syllabus Processing: Convert syllabus text into structured Syllabus model.
    3. PYQ Analysis: Analyze past papers against syllabus.
    4. Blueprint: Build exam blueprint.
    5. Generation: Generate Practice Paper 1 and Practice Paper 2.
    6. Validation: Verify generated papers.
    """
    # Step 1: Ingest PYQ files
    pyq_texts = []
    for file_source, filename in pyq_files:
        if file_source:
            text = extract_and_clean_document(file_source, filename)
            if text.strip():
                pyq_texts.append(text)

    if not pyq_texts:
        raise ValueError("Please upload at least 1 valid Previous Year Question paper (3 recommended).")

    # Step 1b: Ingest Syllabus
    file_source_or_text, filename = syllabus_file_or_text
    if filename:
        syllabus_text = extract_and_clean_document(file_source_or_text, filename)
    else:
        syllabus_text = str(file_source_or_text).strip()

    if not syllabus_text:
        raise ValueError("Please provide a valid Syllabus document or text.")

    import time

    # Step 2: Structured Syllabus Processing
    syllabus = parse_syllabus(syllabus_text)
    time.sleep(1)

    # Filter/default selected modules
    all_module_names = [m.module_name for m in syllabus.modules]
    if not selected_module_names:
        target_modules = all_module_names
    else:
        target_modules = [m for m in selected_module_names if m in all_module_names] or all_module_names

    # Step 3: PYQ Pattern Analysis
    pyq_analysis = analyze_pyqs(pyq_texts, syllabus)
    time.sleep(1)

    # Auto-index into Historical PYQ Intelligence
    try:
        from services.pyq_service import get_pyq_service
        pyq_service = get_pyq_service()
        pyq_service.index_pyq_analyses(
            subject_name=syllabus.subject_name or "General",
            pyq_questions=[q.model_dump() for q in pyq_analysis.question_analyses]
        )
    except Exception as pyq_idx_err:
        print(f"[PYQ Intelligence] Auto-index warning: {pyq_idx_err}")

    # Step 4: Exam Blueprint
    blueprint = create_exam_blueprint(
        syllabus=syllabus,
        pyq_analysis=pyq_analysis,
        paper_type=paper_type,
        total_marks=total_marks,
        selected_modules=target_modules,
        custom_instructions=custom_instructions
    )
    time.sleep(1)

    # Step 5: Question Generation
    paper_set = generate_practice_papers(
        syllabus=syllabus,
        pyq_analysis=pyq_analysis,
        blueprint=blueprint,
        custom_instructions=custom_instructions
    )

    # Step 6: Output Validation
    validation_result = validate_paper_set(paper_set, blueprint)

    return {
        "success": True,
        "syllabus": syllabus.model_dump(),
        "pyq_analysis": pyq_analysis.model_dump(),
        "blueprint": blueprint.model_dump(),
        "paper_set": paper_set.model_dump(),
        "validation": validation_result
    }
