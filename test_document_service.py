import os
import sys
import io
from pypdf import PdfWriter

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

from services.document_service import (
    extract_text_from_file,
    clean_and_normalize_text,
    extract_and_clean_document
)

# --------------------------------------------------
# Test 1: Plain Text Document Extraction
# --------------------------------------------------
print("Test 1: Plain Text Document Ingestion...")

sample_text_content = """
========================================
MODULE 1: OPERATING SYSTEMS OVERVIEW
========================================
Topics: Process Management, Memory Management, File Systems.

Question 1 (10 Marks):
Explain the difference between process and thread with suitable diagrams.
"""

cleaned_txt = clean_and_normalize_text(sample_text_content)
assert "MODULE 1: OPERATING SYSTEMS OVERVIEW" in cleaned_txt
assert "Question 1 (10 Marks):" in cleaned_txt
print("   Plain text extraction & cleaning PASSED! 💥")


# --------------------------------------------------
# Test 2: PDF Document Creation & Ingestion
# --------------------------------------------------
print("\nTest 2: PDF Document Ingestion with pypdf...")

writer = PdfWriter()
writer.add_blank_page(width=612, height=792)

# Save test PDF to uploads directory
os.makedirs("uploads", exist_ok=True)
test_pdf_path = os.path.join("uploads", "sample_test_paper.pdf")

with open(test_pdf_path, "wb") as f:
    writer.write(f)

# Extract from created PDF
pdf_text = extract_and_clean_document(test_pdf_path, "sample_test_paper.pdf")
print("   PDF created and opened successfully!")
print("   Extracted PDF Text Length:", len(pdf_text))

# Clean up test file
if os.path.exists(test_pdf_path):
    os.remove(test_pdf_path)


# --------------------------------------------------
# Test 3: Byte Stream Ingestion (Flask request.files simulation)
# --------------------------------------------------
print("\nTest 3: File Storage Stream Simulation...")

fake_file_stream = io.BytesIO(b"Module 2: CPU Scheduling\n\nExplain Round Robin scheduling algorithm.   (5 Marks)")
extracted_from_stream = extract_and_clean_document(fake_file_stream, "pyq_paper1.txt")

assert "Module 2: CPU Scheduling" in extracted_from_stream
assert "(5 Marks)" in extracted_from_stream
print("   Byte stream extraction PASSED! 💥")

print("\nALL DOCUMENT INGESTION TESTS PASSED SUCCESSFULLY! 💥")
