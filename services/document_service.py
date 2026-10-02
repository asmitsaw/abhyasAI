import os
import re
import io
from pypdf import PdfReader


def extract_text_from_file(file_source, filename: str) -> str:
    """
    Extract raw text from a PDF, TXT, or Markdown document.
    'file_source' can be a file path string or a file-like byte stream.
    """
    if not filename:
        raise ValueError("Filename is required to detect document format.")

    extension = os.path.splitext(filename)[1].lower()

    if extension == ".pdf":
        return _extract_from_pdf(file_source)
    elif extension in [".txt", ".md", ".csv", ".text"]:
        return _extract_from_text_file(file_source)
    else:
        raise ValueError(f"Unsupported file format: '{extension}'. Supported formats: PDF, TXT, MD.")


def _extract_from_pdf(file_source) -> str:
    """
    Extract text pages from a PDF stream or file path.
    """
    text_content = []

    try:
        if isinstance(file_source, (str, bytes, os.PathLike)):
            reader = PdfReader(file_source)
        else:
            # File-like object (e.g. Werkzeug FileStorage stream)
            reader = PdfReader(file_source)

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_content.append(f"--- PAGE {page_num} ---\n{page_text}")

    except Exception as error:
        raise RuntimeError(f"Failed to extract text from PDF: {error}")

    return "\n\n".join(text_content)


def _extract_from_text_file(file_source) -> str:
    """
    Extract text from plain text or Markdown document stream, path, or string.
    """
    try:
        if isinstance(file_source, (str, os.PathLike)):
            if os.path.exists(file_source):
                with open(file_source, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            else:
                # If it's a raw string containing document text
                return str(file_source)
        elif isinstance(file_source, bytes):
            return file_source.decode("utf-8", errors="ignore")
        elif hasattr(file_source, "read"):
            content = file_source.read()
            if isinstance(content, bytes):
                return content.decode("utf-8", errors="ignore")
            return str(content)
        else:
            return str(file_source)
    except Exception as error:
        raise RuntimeError(f"Failed to read text file: {error}")


def clean_and_normalize_text(raw_text: str) -> str:
    """
    Clean up extracted document text by stripping control characters
    and normalizing irregular spacing and linebreaks.
    """
    if not raw_text:
        return ""

    # Remove non-printable control characters except standard line breaks and tabs
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)

    # Normalize carriage returns to standard newlines
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

    # Replace multiple consecutive spaces with a single space
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    # Replace 3 or more consecutive newlines with 2 newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()


def extract_and_clean_document(file_source, filename: str) -> str:
    """
    Combined helper: extracts raw text and applies cleaning/normalization.
    """
    raw_text = extract_text_from_file(file_source, filename)
    return clean_and_normalize_text(raw_text)
