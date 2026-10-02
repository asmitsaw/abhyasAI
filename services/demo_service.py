from datetime import datetime
from typing import Any, Dict
from models.database import init_db, SessionLocal, User, Subject, StudentTopicMastery
from services.pyq_service import get_pyq_service
from services.rag.ingestion import UniversalIngestionService


SAMPLE_OS_SYLLABUS = """
SUBJECT: OPERATING SYSTEMS (CS301)
MODULE 1: PROCESS MANAGEMENT
Topics: Process state transitions, Process control blocks, CPU scheduling algorithms (FCFS, SJF, Priority, Round Robin), Inter-process communication (pipes, shared memory), Concurrency and Deadlocks (Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait, Banker's Algorithm).

MODULE 2: MEMORY MANAGEMENT
Topics: Address binding, Logical vs Physical address space, Paging, Page tables, Segmentation, Virtual memory, Demand paging, Page replacement algorithms (FIFO, Optimal, LRU), Thrashing and working set model.

MODULE 3: STORAGE AND FILE SYSTEMS
Topics: Disk structure, Disk scheduling algorithms (FCFS, SSTF, SCAN, C-SCAN), File allocation methods (Contiguous, Linked, Indexed), Directory implementation, Free-space management.
"""

SAMPLE_PYQ_QUESTIONS = [
    {
        "question": "Explain Round Robin CPU scheduling algorithm with an example and calculate average waiting time for time quantum = 2ms.",
        "marks": 10,
        "module": "Module 1: Process Management",
        "topic": "CPU Scheduling (FCFS/RR)",
        "question_type": "Numerical & Descriptive",
        "difficulty": "Medium",
        "year": "2024",
        "question_number": "Q3(a)"
    },
    {
        "question": "What is a Deadlock? Explain the four necessary conditions for deadlock occurrence with real-world examples.",
        "marks": 7,
        "module": "Module 1: Process Management",
        "topic": "Deadlocks & Banker's Algorithm",
        "question_type": "Descriptive",
        "difficulty": "Medium",
        "year": "2024",
        "question_number": "Q4(a)"
    },
    {
        "question": "Solve the Banker's algorithm matrix problem to determine whether the system is in a safe state and find the safe execution sequence.",
        "marks": 10,
        "module": "Module 1: Process Management",
        "topic": "Deadlocks & Banker's Algorithm",
        "question_type": "Numerical / Algorithmic",
        "difficulty": "Hard",
        "year": "2025",
        "question_number": "Q2"
    },
    {
        "question": "Differentiate between Paging and Segmentation with neat architecture diagrams and address translation flow.",
        "marks": 10,
        "module": "Module 2: Memory Management",
        "topic": "Paging & Segmentation",
        "question_type": "Diagram-based & Comparative",
        "difficulty": "Medium",
        "year": "2025",
        "question_number": "Q5(a)"
    },
    {
        "question": "Explain LRU and FIFO page replacement algorithms for reference string: 7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2 and count page faults.",
        "marks": 10,
        "module": "Module 2: Memory Management",
        "topic": "Page Replacement (FIFO/LRU)",
        "question_type": "Numerical",
        "difficulty": "Hard",
        "year": "2026",
        "question_number": "Q3(b)"
    },
    {
        "question": "Explain Process State Transition diagram with 5 states (New, Ready, Running, Waiting, Terminated) and dispatch transitions.",
        "marks": 5,
        "module": "Module 1: Process Management",
        "topic": "Process State Transitions",
        "question_type": "Diagram-based",
        "difficulty": "Easy",
        "year": "2024",
        "question_number": "Q1(a)"
    },
    {
        "question": "Compare FCFS, SSTF, and SCAN disk scheduling algorithms on a request queue of cylinders.",
        "marks": 8,
        "module": "Module 3: Storage & File Systems",
        "topic": "Disk Scheduling (SSTF/SCAN)",
        "question_type": "Comparative & Numerical",
        "difficulty": "Medium",
        "year": "2026",
        "question_number": "Q6"
    }
]


def seed_demo_data() -> Dict[str, Any]:
    """
    Populates SQLite database and RAG collections with Operating Systems benchmark data.
    Ensures hackathon demo is immediate and 100% reliable.
    """
    init_db()
    db = SessionLocal()
    try:
        # 1. User
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, username="demostudent", email="student@abhyas.ai")
            db.add(user)
            db.commit()

        # 2. Subject
        subject = db.query(Subject).filter(Subject.name == "Operating Systems").first()
        if not subject:
            subject = Subject(name="Operating Systems", code="CS301", syllabus_json=SAMPLE_OS_SYLLABUS)
            db.add(subject)
            db.commit()

        # 3. Seed Topic Masteries
        demo_masteries = [
            ("Deadlocks & Banker's Algorithm", "Module 1: Process Management", 38.0, 0.4, 5, 2),
            ("Paging & Segmentation", "Module 2: Memory Management", 42.0, 0.5, 6, 3),
            ("CPU Scheduling (FCFS/RR)", "Module 1: Process Management", 64.0, 0.7, 8, 5),
            ("Process State Transitions", "Module 1: Process Management", 82.0, 0.9, 10, 8),
            ("Page Replacement (FIFO/LRU)", "Module 2: Memory Management", 48.0, 0.5, 4, 2),
            ("Disk Scheduling (SSTF/SCAN)", "Module 3: Storage & File Systems", 70.0, 0.8, 7, 5),
            ("Inter-process Communication", "Module 1: Process Management", 55.0, 0.6, 5, 3)
        ]

        for topic, module, score, conf, attempts, corrects in demo_masteries:
            record = db.query(StudentTopicMastery).filter(
                StudentTopicMastery.student_id == 1,
                StudentTopicMastery.topic_name == topic
            ).first()

            if not record:
                record = StudentTopicMastery(
                    student_id=1,
                    subject_id=subject.id,
                    topic_name=topic,
                    module_name=module,
                    mastery_score=score,
                    confidence=conf,
                    attempt_count=attempts,
                    correct_count=corrects,
                    last_attempt=datetime.utcnow(),
                    last_correct=datetime.utcnow()
                )
                db.add(record)
            else:
                record.mastery_score = score
                record.confidence = conf
                record.attempt_count = attempts
                record.correct_count = corrects
        db.commit()

        # 4. Seed PYQ Historical Intelligence
        pyq_service = get_pyq_service()
        pyq_service.index_pyq_analyses(
            subject_name="Operating Systems",
            pyq_questions=SAMPLE_PYQ_QUESTIONS,
            total_historical_marks=180
        )

        # 5. Ingest Syllabus into RAG
        try:
            ingestion = UniversalIngestionService()
            ingestion.ingest_raw_text(
                text=SAMPLE_OS_SYLLABUS,
                title="Operating Systems Official Syllabus (CS301)",
                document_type="syllabus",
                subject="Operating Systems"
            )
            # Ingest sample PYQ summary
            pyq_combined_text = "\n\n".join([f"Year {q['year']} Question {q['question_number']} ({q['marks']} Marks): {q['question']}" for q in SAMPLE_PYQ_QUESTIONS])
            ingestion.ingest_raw_text(
                text=pyq_combined_text,
                title="Past Year Examination Papers (2024-2026)",
                document_type="pyq",
                subject="Operating Systems"
            )
        except Exception as rag_err:
            print(f"[Demo] RAG ingestion warning: {rag_err}")

        return {
            "status": "success",
            "message": "Demo mode initialized with Operating Systems benchmark curriculum.",
            "student_id": 1,
            "subject": "Operating Systems",
            "topics_seeded": len(demo_masteries),
            "pyqs_indexed": len(SAMPLE_PYQ_QUESTIONS)
        }
    finally:
        db.close()
