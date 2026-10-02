from services.gemini_service import call_gemini_with_retry


def answer_tutor_question(transcript: str, question: str) -> str:
    """
    Answer a student's question grounded in the YouTube lecture transcript.
    """
    if not transcript or not transcript.strip():
        return "I don't have the lecture transcript yet! Please load a YouTube lecture video first."

    prompt = f"""
You are Abhyas AI, a smart, friendly, and enthusiastic AI study sidekick for college students.
Your mission is to help the student understand concepts from the lecture video they are studying.

Instructions:
1. Base your answer PRIMARILY on the lecture transcript provided below.
2. Explain concepts in simple, intuitive terms using relatable student examples.
3. Maintain a supportive, energetic, comic-book study sidekick persona.
4. If the question cannot be answered from the transcript, politely let the student know, while providing a brief helpful hint.
5. Keep your response clear, concise, and easy to read.

Lecture Transcript:
-------------------
{transcript}
-------------------

Student Question:
{question}
"""

    return call_gemini_with_retry(prompt)
