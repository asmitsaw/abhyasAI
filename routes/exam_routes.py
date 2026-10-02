from flask import Blueprint, render_template, request, jsonify
from services.exam_prep_pipeline import run_exam_prep_pipeline

exam_bp = Blueprint('exam', __name__, url_prefix='/exam')


@exam_bp.route('/')
@exam_bp.route('')
def exam_prep_page():
    return render_template('exam/prep.html')


@exam_bp.route('/generate', methods=['POST'])
def generate_exam_papers():
    try:
        # Collect PYQ files
        pyq_files = []
        
        # Check for multiple files in pyq_files or individual pyq1, pyq2, pyq3
        uploaded_pyqs = request.files.getlist('pyq_files')
        for f in uploaded_pyqs:
            if f and f.filename:
                pyq_files.append((f.stream, f.filename))
        
        for key in ['pyq1', 'pyq2', 'pyq3']:
            if key in request.files:
                f = request.files[key]
                if f and f.filename:
                    pyq_files.append((f.stream, f.filename))

        # Collect Syllabus
        syllabus_file = request.files.get('syllabus_file')
        syllabus_text_input = request.form.get('syllabus_text', '').strip()

        if syllabus_file and syllabus_file.filename:
            syllabus_tuple = (syllabus_file.stream, syllabus_file.filename)
        elif syllabus_text_input:
            syllabus_tuple = (syllabus_text_input, None)
        else:
            return jsonify({
                "success": False,
                "error": "Please upload a syllabus file or paste syllabus text."
            }), 400

        # Collect Form Settings
        paper_type = request.form.get('paper_type', 'Unit Test').strip()
        format_pattern = request.form.get('format_pattern', '').strip()
        try:
            total_marks = int(request.form.get('total_marks', 30))
        except ValueError:
            total_marks = 30

        selected_modules = request.form.getlist('selected_modules')
        custom_instructions = request.form.get('custom_instructions', '').strip()

        if format_pattern:
            if custom_instructions:
                custom_instructions = f"Paper Format Standard: {format_pattern}. " + custom_instructions
            else:
                custom_instructions = f"Paper Format Standard: {format_pattern}."

        # Run pipeline
        result = run_exam_prep_pipeline(
            pyq_files=pyq_files,
            syllabus_file_or_text=syllabus_tuple,
            paper_type=paper_type,
            total_marks=total_marks,
            selected_module_names=selected_modules,
            custom_instructions=custom_instructions
        )

        return jsonify(result)

    except Exception as error:
        print(f"Exam Prep Generation Error: {error}")
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
