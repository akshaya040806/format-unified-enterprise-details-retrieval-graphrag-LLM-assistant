"""
Veltrix Systems — Admin Document Ingestion Pipeline
Converts uploaded files (PDF, DOCX, TXT, CSV, audio) to JSON
and integrates them into the RAG dataset.

Admins upload → this converts → saves to data/ → RAG re-indexes
"""

import json
import os
import re
import datetime

UPLOAD_DIR   = "./uploads"
DATA_DIR     = "./data"
DATASET_FILE = "./data/_all_conversations.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR,   exist_ok=True)


def extract_text_from_file(filepath: str, filename: str) -> str:
    """Route to the correct extractor based on file extension."""
    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "txt":
        return _extract_txt(filepath)
    elif ext == "pdf":
        return _extract_pdf(filepath)
    elif ext == "docx":
        return _extract_docx(filepath)
    elif ext in ("csv", "xlsx"):
        return _extract_tabular(filepath, ext)
    elif ext in ("mp3", "wav", "m4a", "mp4", "mov"):
        return _extract_audio(filepath)
    else:
        return _extract_txt(filepath)  # fallback: try as plain text


def _extract_txt(filepath):
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[Extraction error: {e}]"


def _extract_pdf(filepath):
    try:
        import pymupdf
        doc   = pymupdf.open(filepath)
        pages = [page.get_text() for page in doc]
        return "\n\n".join(pages)
    except ImportError:
        return "[PDF extraction requires: pip install pymupdf]"
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _extract_docx(filepath):
    try:
        from docx import Document
        doc   = Document(filepath)
        lines = []
        for para in doc.paragraphs:
            if para.text.strip():
                prefix = "## " if para.style.name.startswith("Heading") else ""
                lines.append(f"{prefix}{para.text}")
        for table in doc.tables:
            for row in table.rows:
                cells = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if cells:
                    lines.append(cells)
        return "\n".join(lines)
    except ImportError:
        return "[DOCX extraction requires: pip install python-docx]"
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def _extract_tabular(filepath, ext):
    try:
        import pandas as pd
        if ext == "csv":
            import chardet
            with open(filepath, "rb") as f:
                enc = chardet.detect(f.read())["encoding"] or "utf-8"
            df = pd.read_csv(filepath, encoding=enc)
        else:
            df = pd.read_excel(filepath, sheet_name=None, engine="openpyxl")
            if isinstance(df, dict):
                parts = []
                for sheet, sdf in df.items():
                    sdf = sdf.fillna("")
                    rows = [" | ".join(f"{col}: {row[col]}" for col in sdf.columns)
                            for _, row in sdf.iterrows()]
                    parts.append(f"[Sheet: {sheet}]\n" + "\n".join(rows))
                return "\n\n".join(parts)

        df = df.fillna("")
        rows = [" | ".join(f"{col}: {row[col]}" for col in df.columns)
                for _, row in df.iterrows()]
        return "\n".join(rows)
    except ImportError:
        return "[Tabular extraction requires: pip install pandas openpyxl chardet]"
    except Exception as e:
        return f"[Tabular extraction error: {e}]"


def _extract_audio(filepath):
    try:
        from faster_whisper import WhisperModel
        model    = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(filepath)
        lines    = [f"[{seg.start:.1f}s] {seg.text.strip()}" for seg in segments]
        return "\n".join(lines)
    except ImportError:
        return "[Audio transcription requires: pip install faster-whisper]"
    except Exception as e:
        return f"[Audio transcription error: {e}]"


def convert_to_document_record(
    text:        str,
    filename:    str,
    project:     str,
    description: str,
    added_by:    str,
    fmt:         str,
) -> dict:
    """
    Wrap extracted text into the same JSON structure the RAG engine expects,
    so it can be indexed exactly like generated conversation data.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc_id    = f"admin_upload_{filename.replace(' ', '_')}_{timestamp[:10]}"

    # Split long text into message-like chunks (paragraphs or lines)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}|\r\n{2,}", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text[:2000]] if text.strip() else ["[Empty document]"]

    messages = []
    for i, para in enumerate(paragraphs[:100]):  # cap at 100 chunks
        messages.append({
            "sender":    added_by,
            "text":      para,
            "timestamp": timestamp,
        })

    return {
        "doc_id":          doc_id,
        "conversation_id": doc_id,
        "project":         project,
        "format":          fmt,
        "platform":        fmt,
        "stage_title":     description or f"Admin-uploaded document: {filename}",
        "completion_pct":  100,
        "participants":    [added_by],
        "source":          "admin_upload",
        "filename":        filename,
        "added_by":        added_by,
        "added_at":        timestamp,
        "messages":        messages,
        "metadata": {
            "source":      "admin_upload",
            "format":      fmt,
            "project":     project,
            "filename":    filename,
            "description": description,
        }
    }


def add_document_to_dataset(record: dict) -> tuple[bool, str]:
    """Append the new document record to the main dataset file."""
    try:
        if os.path.exists(DATASET_FILE):
            with open(DATASET_FILE) as f:
                dataset = json.load(f)
        else:
            dataset = []

        # Check for duplicates by doc_id
        existing_ids = {d.get("doc_id") for d in dataset}
        if record["doc_id"] in existing_ids:
            record["doc_id"] += "_v2"

        dataset.append(record)

        with open(DATASET_FILE, "w") as f:
            json.dump(dataset, f, indent=2)

        return True, f"Document added. Dataset now has {len(dataset)} records."
    except Exception as e:
        return False, f"Failed to add to dataset: {e}"


def process_uploaded_file(
    file_bytes:  bytes,
    filename:    str,
    project:     str,
    description: str,
    added_by:    str,
) -> dict:
    """
    Full pipeline:
    1. Save uploaded bytes to disk
    2. Extract text based on format
    3. Convert to document record
    4. Add to dataset
    5. Return result dict for UI feedback
    """
    fmt       = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
    save_path = os.path.join(UPLOAD_DIR, filename)

    # Save to disk
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Extract text
    text = extract_text_from_file(save_path, filename)
    word_count = len(text.split())

    if word_count < 5:
        return {
            "success":    False,
            "message":    f"Could not extract meaningful text from {filename}. Got: {text[:200]}",
            "word_count": word_count,
        }

    # Build record and add to dataset
    record   = convert_to_document_record(text, filename, project, description, added_by, fmt)
    ok, msg  = add_document_to_dataset(record)

    return {
        "success":      ok,
        "message":      msg,
        "filename":     filename,
        "format":       fmt,
        "project":      project,
        "word_count":   word_count,
        "chunks_added": len(record["messages"]),
        "doc_id":       record["doc_id"],
        "needs_reindex": ok,
    }