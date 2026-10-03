import io
import csv
from typing import List
from services.document_service import clean_and_normalize_text
from services.ingestion.models import ExtractedChunk, NormalizedDocument


def parse_spreadsheet(file_bytes: bytes, filename: str) -> NormalizedDocument:
    """
    Parse CSV or Excel spreadsheet (.csv, .xlsx, .xls) into structured text.
    """
    ext = filename.lower().split(".")[-1]
    chunks: List[ExtractedChunk] = []
    text_blocks: List[str] = []

    if ext == "csv":
        text_data = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text_data))
        rows = list(reader)
        if rows:
            header = rows[0]
            table_lines = [" | ".join(header), " | ".join(["---"] * len(header))]
            for row in rows[1:100]:  # up to 100 rows per chunk
                if any(row):
                    table_lines.append(" | ".join(row))
            table_str = "\n".join(table_lines)
            text_blocks.append(f"--- SHEET: Data ---\n{table_str}")
            chunks.append(ExtractedChunk(
                text=table_str,
                page=1,
                sheet="Data",
                section="CSV Table",
                heading="Table Data",
                source_type="csv"
            ))
    else:
        # Excel (.xlsx) using openpyxl
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            for sheet_idx, sheet_name in enumerate(wb.sheetnames, 1):
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    continue

                non_empty_rows = [r for r in rows if any(cell is not None for cell in r)]
                if not non_empty_rows:
                    continue

                header = [str(c or "") for c in non_empty_rows[0]]
                table_lines = [" | ".join(header), " | ".join(["---"] * len(header))]

                for r in non_empty_rows[1:100]:
                    cells = [str(c if c is not None else "") for c in r]
                    table_lines.append(" | ".join(cells))

                sheet_text = f"--- SHEET: {sheet_name} ---\n" + "\n".join(table_lines)
                text_blocks.append(sheet_text)
                chunks.append(ExtractedChunk(
                    text="\n".join(table_lines),
                    page=sheet_idx,
                    sheet=sheet_name,
                    section=f"Sheet: {sheet_name}",
                    heading=sheet_name,
                    source_type="excel"
                ))
        except Exception as e:
            text_blocks.append(f"Spreadsheet {filename}: raw data parsed with notice ({e}).")

    all_text = "\n\n".join(text_blocks)
    return NormalizedDocument(
        text=all_text,
        original_filename=filename,
        source_type="spreadsheet",
        mime_type="application/vnd.ms-excel",
        file_extension=f".{ext}",
        file_size=len(file_bytes),
        page_count=max(1, len(chunks)),
        chunks=chunks
    )
