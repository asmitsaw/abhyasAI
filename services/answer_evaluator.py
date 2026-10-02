import json
from typing import Any, Dict, List, Optional
from services.llm.provider_factory import get_llm_provider
from services.rag.rag_pipeline import get_rag_pipeline


class AnswerEvaluator:
    """
    Evaluates student answers against structured, evidence-grounded rubrics.
    Also provides 'Exam Answer Mode' generating optimal answer structures for 2, 5, 10, or 15 marks.
    """

    def __init__(self, provider: Optional[Any] = None, rag: Optional[Any] = None):
        self.provider = provider or get_llm_provider()
        self.rag = rag or get_rag_pipeline()

    def build_rubric(
        self,
        question: str,
        max_marks: int,
        topic: str = "",
        context_text: str = ""
    ) -> Dict[str, Any]:
        """
        Constructs an objective marking rubric based on academic standards and marks allocation.
        """
        if max_marks <= 2:
            return {
                "max_marks": max_marks,
                "criteria": [
                    {"name": "Core Definition & Precision", "marks": 1.5, "expectation": "Accurate technical definition with appropriate keywords"},
                    {"name": "Keyword / Example", "marks": 0.5, "expectation": "One relevant keyword, formula, or concise example"}
                ],
                "expected_sections": ["Definition", "Key Term / Example"]
            }
        elif max_marks <= 5:
            return {
                "max_marks": max_marks,
                "criteria": [
                    {"name": "Definition & Purpose", "marks": 1.5, "expectation": "Clear concept definition and fundamental purpose"},
                    {"name": "Working Principle / Steps", "marks": 2.0, "expectation": "Accurate step-by-step description or workflow"},
                    {"name": "Example or Diagram sketch", "marks": 1.5, "expectation": "Concrete illustration or block diagram reference"}
                ],
                "expected_sections": ["Definition", "Working / Mechanism", "Example & Application"]
            }
        elif max_marks <= 10:
            return {
                "max_marks": max_marks,
                "criteria": [
                    {"name": "Technical Definition & Background", "marks": 2.0, "expectation": "Formal academic definition, context, and necessity"},
                    {"name": "Detailed Architecture / Mechanism", "marks": 3.0, "expectation": "In-depth explanation with neat diagram reference or algorithm"},
                    {"name": "Concrete Example / Numerical Case", "marks": 2.0, "expectation": "Comprehensive walk-through example"},
                    {"name": "Advantages & Limitations", "marks": 2.0, "expectation": "At least 3 valid advantages and 2 limitations"},
                    {"name": "Conclusion / Real-World Use Case", "marks": 1.0, "expectation": "Summary and contemporary OS/hardware context"}
                ],
                "expected_sections": [
                    "Definition & Overview",
                    "Architecture / Block Diagram Description",
                    "Detailed Working / Algorithm",
                    "Concrete Example",
                    "Advantages & Limitations",
                    "Conclusion"
                ]
            }
        else:  # 15 marks
            return {
                "max_marks": max_marks,
                "criteria": [
                    {"name": "Exhaustive Definition & Taxonomy", "marks": 3.0, "expectation": "Deep theoretical foundation and classification"},
                    {"name": "Architectural Diagram & Component Interaction", "marks": 4.0, "expectation": "Comprehensive diagrammatic layout and workflow"},
                    {"name": "Mathematical Formulation / Numerical Problem", "marks": 4.0, "expectation": "Detailed calculation or algorithmic derivation"},
                    {"name": "Comparative Analysis (Trade-offs)", "marks": 2.5, "expectation": "Thorough comparison table with alternative algorithms"},
                    {"name": "Synthesis & Performance Bottlenecks", "marks": 1.5, "expectation": "Critical evaluation of efficiency and edge cases"}
                ],
                "expected_sections": [
                    "Introduction & Theory",
                    "Architecture & Diagrammatic Representation",
                    "Step-by-Step Algorithm / Derivation",
                    "Comparative Analysis Table",
                    "Practical Performance Trade-offs & Limitations",
                    "Conclusion"
                ]
            }

    def evaluate_answer(
        self,
        question: str,
        student_answer: str,
        max_marks: int = 10,
        subject: str = "General",
        topic: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates a submitted student answer against the objective rubric and RAG context.
        """
        # Fetch relevant context from RAG
        rag_context = ""
        try:
            rag_res = self.rag.query(question, subject=subject, top_k=3)
            rag_context = rag_res.get("answer", "")
        except Exception:
            pass

        rubric = self.build_rubric(question, max_marks, topic)
        rubric_json = json.dumps(rubric, indent=2)

        prompt = (
            f"You are a rigorous university examination paper evaluator.\n"
            f"Question ({max_marks} Marks):\n{question}\n\n"
            f"Objective Rubric:\n{rubric_json}\n\n"
            f"Reference Syllabus/Textbook Evidence:\n{rag_context}\n\n"
            f"Student's Submitted Answer:\n{student_answer}\n\n"
            f"Evaluation Guidelines:\n"
            f"1. Score objectively strictly out of {max_marks} based on the rubric.\n"
            f"2. Identify specific strengths (what the student got right).\n"
            f"3. Identify missing concepts or terminology required for full marks.\n"
            f"4. Provide exact technical corrections.\n"
            f"5. Provide actionable advice for university examination formatting.\n"
            f"Output strictly valid JSON with keys: 'score', 'max_score', 'strengths', 'missing_concepts', 'corrections', 'ideal_structure', 'improvement_advice'."
        )

        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "max_score": {"type": "integer"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "missing_concepts": {"type": "array", "items": {"type": "string"}},
                "corrections": {"type": "array", "items": {"type": "string"}},
                "ideal_structure": {"type": "array", "items": {"type": "string"}},
                "improvement_advice": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["score", "max_score", "strengths", "missing_concepts", "corrections", "ideal_structure", "improvement_advice"]
        }

        try:
            res = self.provider.generate_json(prompt=prompt, schema=schema)
            data = json.loads(res)
            data["max_score"] = max_marks
            data["score"] = round(min(float(max_marks), max(0.0, float(data.get("score", max_marks * 0.5)))), 1)
            data["rubric_used"] = rubric
            return data
        except Exception as error:
            print(f"Answer evaluation parsing error: {error}")
            # Fallback deterministic evaluation
            word_count = len(student_answer.split())
            heuristic_score = min(float(max_marks), max(1.0, (word_count / 150.0) * max_marks))
            return {
                "score": round(heuristic_score, 1),
                "max_score": max_marks,
                "strengths": ["Answer demonstrates foundational awareness of the topic."],
                "missing_concepts": ["Include more specific academic terminology and structural headings."],
                "corrections": ["Ensure diagrammatic representation is referenced for high mark allocations."],
                "ideal_structure": rubric.get("expected_sections", []),
                "improvement_advice": ["Format response into distinct numbered paragraphs with bold keywords."],
                "rubric_used": rubric
            }

    def generate_exam_answer_template(
        self,
        question: str,
        marks: int = 10,
        subject: str = "General"
    ) -> Dict[str, Any]:
        """
        EXAM ANSWER MODE:
        Generates an exemplar, model answer tailored to 2, 5, 10, or 15 marks.
        """
        rubric = self.build_rubric(question, marks)
        expected_sections = rubric.get("expected_sections", [])

        prompt = (
            f"You are an expert university professor creating an exemplar model answer.\n"
            f"Subject: {subject}\n"
            f"Question: {question}\n"
            f"Target Marks: {marks} Marks\n"
            f"Required Sections:\n" + "\n".join(f"- {s}" for s in expected_sections) + "\n\n"
            f"Write the definitive model answer formatted exactly as a university topper would write in an exam book.\n"
            f"Include clear section headers, bulleted key points, a diagram description block [DIAGRAM: ...], and clear conclusions."
        )

        model_answer = self.provider.generate(prompt=prompt, temperature=0.3)

        return {
            "question": question,
            "target_marks": marks,
            "expected_structure": expected_sections,
            "model_answer": model_answer
        }
