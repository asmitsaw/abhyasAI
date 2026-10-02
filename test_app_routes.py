import sys
sys.stdout.reconfigure(encoding='utf-8')

from app import app, TRANSCRIPT_STORE

client = app.test_client()

print("1. Testing GET / ...")
res = client.get("/")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
print("   / returned 200 OK")

print("2. Testing GET /learn ...")
res = client.get("/learn")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
print("   /learn returned 200 OK")

print("3. Testing POST /ask-tutor without video ...")
res = client.post("/ask-tutor", json={"question": "What is deadlock?"})
assert res.status_code == 400
data = res.get_json()
assert data["success"] is False
print(f"   Response: {data['error']}")

print("4. Testing POST /ask-tutor with mock transcript in store ...")
mock_video_id = "test_vid_123"
TRANSCRIPT_STORE[mock_video_id] = "Operating Systems deadlocks occur when four conditions are met: mutual exclusion, hold and wait, no preemption, and circular wait."

res = client.post("/ask-tutor", json={"question": "What are the four deadlock conditions?", "video_id": mock_video_id})
assert res.status_code == 200
data = res.get_json()
assert data["success"] is True
print("   AI Tutor Response:")
print("   " + data["answer"].replace("\n", "\n   "))

print("\nALL FLASK ROUTE TESTS PASSED SUCCESSFULLY! 💥")
