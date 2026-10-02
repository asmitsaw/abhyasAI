import sys
sys.stdout.reconfigure(encoding='utf-8')

from services.exam_prep_pipeline import run_exam_prep_pipeline

sample_syllabus = """
MODULE 1: PROCESS MANAGEMENT
Topics: Process state transitions, CPU scheduling algorithms (FCFS, SJF, Round Robin), Inter-process communication.

MODULE 2: MEMORY MANAGEMENT
Topics: Paging, Segmentation, Virtual memory, Page replacement algorithms (FIFO, LRU).

MODULE 3: STORAGE AND FILE SYSTEMS
Topics: Disk scheduling (FCFS, SSTF, SCAN), File allocation methods, Deadlock handling (Banker's algorithm).
"""

sample_pyq1 = """
UNIVERSITY END SEMESTER EXAMINATION - OPERATING SYSTEMS (2024)
Time: 3 Hours | Total Marks: 80

Section A (10 Marks)
Q1. Define thread and state two differences between thread and process. (5 Marks)
Q2. Explain page fault and demand paging in short. (5 Marks)

Section B (20 Marks)
Q3. Calculate average waiting time for processes P1, P2, P3 using Round Robin (quantum=2). (10 Marks)
Q4. Explain Banker's Algorithm for deadlock avoidance with safety algorithm. (10 Marks)
"""

sample_pyq2 = """
UNIVERSITY END SEMESTER EXAMINATION - OPERATING SYSTEMS (2025)
Time: 3 Hours | Total Marks: 80

Section A
Q1. Explain LRU page replacement algorithm with example. (5 Marks)
Q2. Compare FCFS and SSTF disk scheduling algorithms. (5 Marks)

Section B
Q3. Explain process state transition diagram with neat sketch. (10 Marks)
Q4. Solve Banker's algorithm matrix problem to check if system is in safe state. (10 Marks)
"""

sample_pyq3 = """
UNIVERSITY UNIT TEST 1 - OPERATING SYSTEMS (2025)
Total Marks: 20

Q1. Short notes on Inter-process Communication (IPC). (5 Marks)
Q2. Calculate page faults for reference string using FIFO algorithm. (5 Marks)
Q3. Explain Virtual Memory concept and Segmentation. (10 Marks)
"""

print("Running Exam Prep End-to-End Pipeline Integration Test...")

result = run_exam_prep_pipeline(
    pyq_files=[
        (sample_pyq1, "pyq1.txt"),
        (sample_pyq2, "pyq2.txt"),
        (sample_pyq3, "pyq3.txt")
    ],
    syllabus_file_or_text=(sample_syllabus, None),
    paper_type="Unit Test",
    total_marks=20,
    selected_module_names=["Module 1: Process Management", "Module 2: Memory Management"],
    custom_instructions="Focus on numerical problems where applicable."
)

print("\nPipeline Result Success:", result["success"])
print("Modules Parsed:", [m["module_name"] for m in result["syllabus"]["modules"]])
print("Validation Result:", result["validation"])

paper_1 = result["paper_set"]["paper_1"]
paper_2 = result["paper_set"]["paper_2"]

print(f"\n--- {paper_1['title']} (Total Marks: {paper_1['total_marks']}) ---")
for sec in paper_1["sections"]:
    print(f"Section: {sec['section_title']}")
    for q in sec["questions"]:
        print(f"  [{q['question_number']}] ({q['marks']} Marks) {q['question_text']}")

print(f"\n--- {paper_2['title']} (Total Marks: {paper_2['total_marks']}) ---")
for sec in paper_2["sections"]:
    print(f"Section: {sec['section_title']}")
    for q in sec["questions"]:
        print(f"  [{q['question_number']}] ({q['marks']} Marks) {q['question_text']}")

print("\nEXAM PREP PIPELINE INTEGRATION TEST COMPLETED SUCCESSFULLY! 💥")
