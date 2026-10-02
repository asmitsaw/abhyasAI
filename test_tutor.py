import sys

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

from services.transcript_service import get_transcript
from services.tutor_service import answer_tutor_question

VIDEO_ID = "dQw4w9WgXcQ"

print("Getting transcript...")
transcript = get_transcript(VIDEO_ID)

if not transcript:
    print("Could not retrieve transcript.")
    raise SystemExit

print("Transcript retrieved!")
print("Testing AI Tutor...")

question = "What is the main topic of this video?"
answer = answer_tutor_question(transcript, question)

print()
print("=" * 60)
print("ABHYAS AI TUTOR RESPONSE")
print("=" * 60)
print(f"Question: {question}")
print(f"Answer:\n{answer}")

