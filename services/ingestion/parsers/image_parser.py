import io
import os
import logging
from typing import List
from PIL import Image

from services.document_service import clean_and_normalize_text
from services.ingestion.models import ExtractedChunk, NormalizedDocument

logger = logging.getLogger("abhyas_ai.ingestion.image")


def parse_image(file_bytes: bytes, filename: str) -> NormalizedDocument:
    """
    Extract educational study material from images using Gemini Multimodal Vision,
    preserving formulas, diagrams, concept labels, and text.
    Falls back gracefully if offline or API key absent.
    """
    ext = os.path.splitext(filename)[1].lower()
    img_format = ext.replace(".", "").upper()
    if img_format == "JPG":
        img_format = "JPEG"

    extracted_text = ""
    # 1. Attempt Multimodal Vision via Google GenAI Client
    try:
        from services.gemini_service import client, PRIMARY_MODEL
        pil_image = Image.open(io.BytesIO(file_bytes))

        prompt = (
            "You are AbhyasAI's academic document extractor. "
            "Examine this study material image (diagram, lecture slide photo, handwritten notes, or textbook snippet). "
            "Extract ALL text, concepts, formulas, headings, bullet points, and explain any architectural diagram or chart "
            "so it is fully searchable in our university RAG vector database. "
            "Return the transcribed and described content in clean, structured markdown."
        )

        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=[pil_image, prompt]
        )
        if response and response.text:
            extracted_text = clean_and_normalize_text(response.text)
            logger.info(f"Successfully extracted {len(extracted_text)} chars from {filename} via Gemini Vision.")
    except Exception as e:
        logger.warning(f"Gemini vision extraction notice for {filename}: {e}. Falling back to basic metadata.")

    # 2. Fallback if Gemini Vision is unavailable or yielded empty text
    if not extracted_text:
        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
            width, height = pil_image.size
            extracted_text = (
                f"### Image Document: {filename}\n"
                f"Image Format: {img_format}, Dimensions: {width}x{height} px.\n"
                f"Study Diagram Reference: {os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()}"
            )
        except Exception:
            extracted_text = f"Study Diagram Reference: {filename}"

    chunk = ExtractedChunk(
        text=extracted_text,
        page=1,
        section="Image Content",
        heading=f"Diagram: {filename}",
        source_type="image"
    )

    return NormalizedDocument(
        text=extracted_text,
        original_filename=filename,
        source_type="image",
        mime_type=f"image/{ext.replace('.', '')}",
        file_extension=ext,
        file_size=len(file_bytes),
        page_count=1,
        chunks=[chunk]
    )
