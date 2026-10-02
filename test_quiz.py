from services.transcript_service import get_transcript
from services.quiz_service import generate_quiz


VIDEO_ID = "dQw4w9WgXcQ"


print("Getting transcript...")

transcript = get_transcript(VIDEO_ID)


if not transcript:

    print("Could not retrieve transcript.")

    raise SystemExit


print("Transcript retrieved!")

print("Generating quiz with Gemini...")

quiz = generate_quiz(transcript)


print()
print("=" * 60)
print("ABHYAS AI QUIZ")
print("=" * 60)


for number, question in enumerate(
    quiz.questions,
    start=1
):

    print()
    print(f"Question {number}:")
    print(question.question)

    print()

    for index, option in enumerate(
        question.options
    ):

        print(
            f"{chr(65 + index)}. {option}"
        )

    print()

    print(
        f"Correct Answer: "
        f"{question.correct_answer}"
    )

    print(
        f"Difficulty: "
        f"{question.difficulty}"
    )

    print(
        f"Explanation: "
        f"{question.explanation}"
    )