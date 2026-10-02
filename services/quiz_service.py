from typing import List
from pydantic import BaseModel, Field
from services.gemini_service import call_gemini_with_retry


class QuizQuestion(BaseModel):
    question: str = Field(
        description="The quiz question."
    )

    options: List[str] = Field(
        description="Exactly four answer options."
    )

    correct_answer: str = Field(
        description="The exact correct answer from the four options."
    )

    explanation: str = Field(
        description="A short explanation of why the answer is correct."
    )

    difficulty: str = Field(
        description="Question difficulty: Easy, Medium, or Hard."
    )


class Quiz(BaseModel):
    questions: List[QuizQuestion] = Field(
        description="Exactly 20 multiple-choice questions."
    )


def generate_quiz(transcript):
    """
    Generate exactly 20 MCQs from a YouTube transcript.
    """

    prompt = f"""
You are Abhyas AI, an AI study assistant for college students.

Create a practice quiz based ONLY on the transcript provided below.

Requirements:

1. Generate exactly 20 multiple-choice questions.
2. Each question must have exactly 4 options.
3. There must be exactly one correct answer.
4. The correct answer must exactly match one of the four options.
5. Include a short explanation for every answer.
6. Assign each question one difficulty:
   Easy, Medium, or Hard.
7. Cover different concepts from the transcript.
8. Do not ask questions about information that is not present
   in the transcript.
9. Avoid duplicate or nearly duplicate questions.
10. Make the questions useful for a college student preparing
    for an examination.

Transcript:

-------------------------
{transcript}
-------------------------
"""

    response_text = call_gemini_with_retry(
        prompt=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": Quiz.model_json_schema()
        }
    )

    quiz = Quiz.model_validate_json(response_text)
    return quiz