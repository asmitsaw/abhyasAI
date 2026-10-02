import sys
import io
sys.stdout.reconfigure(encoding='utf-8')

from app import app, TRANSCRIPT_STORE

client = app.test_client()

print("==================================================")
print("ABHYAS AI - FULL SYSTEM VERIFICATION SUITE")
print("==================================================")

# 1. Homepage Route
print("\n[1/5] Testing GET / (Homepage)...", flush=True)
res = client.get("/")
assert res.status_code == 200
assert b"ABHYAS" in res.data
print("   GET / PASSED 💥", flush=True)

# 2. Abhyas Learn Route
print("\n[2/5] Testing GET /learn (Abhyas Learn)...", flush=True)
res = client.get("/learn")
assert res.status_code == 200
assert b"ABHYAS LEARN" in res.data
print("   GET /learn PASSED 💥", flush=True)

# 3. Abhyas Exam Prep Route
print("\n[3/5] Testing GET /exam (Abhyas Exam Prep)...", flush=True)
res = client.get("/exam", follow_redirects=True)
print(f"   Status code: {res.status_code}", flush=True)
assert res.status_code == 200
assert b"EXAM PREP" in res.data
print("   GET /exam PASSED 💥", flush=True)

# 4. AI Tutor Route
print("\n[4/5] Testing POST /ask-tutor with active transcript...", flush=True)
mock_video_id = "test_vid_abc"
TRANSCRIPT_STORE[mock_video_id] = "Process scheduling algorithms include FCFS, SJF, and Round Robin."

res = client.post("/ask-tutor", json={
    "question": "What is FCFS scheduling?",
    "video_id": mock_video_id
})
assert res.status_code == 200
data = res.get_json()
assert data["success"] is True
assert len(data["answer"]) > 10
print("   POST /ask-tutor PASSED 💥", flush=True)

# 5. Exam Prep Paper Generation Route
print("\n[5/5] Testing POST /exam/generate (End-to-End Exam Prep)...", flush=True)
sample_syllabus = "Module 1: Process Management (Scheduling, Deadlocks)\nModule 2: Memory Management (Paging)"
sample_pyq = "Q1. Explain Round Robin scheduling. (5 Marks)\nQ2. What is Paging? (5 Marks)\nQ3. Explain Deadlock conditions. (10 Marks)"

res = client.post("/exam/generate", data={
    "syllabus_text": sample_syllabus,
    "pyq1": (io.BytesIO(sample_pyq.encode('utf-8')), "pyq1.txt"),
    "paper_type": "Unit Test",
    "total_marks": "20"
})

assert res.status_code == 200
data = res.get_json()
assert data["success"] is True
assert "paper_1" in data["paper_set"]
assert "paper_2" in data["paper_set"]
assert data["validation"]["is_valid"] is True
print("   POST /exam/generate PASSED 💥", flush=True)

print("\nALL ABHYAS AI SYSTEM TESTS PASSED SUCCESSFULLY! 💥🚀", flush=True)
