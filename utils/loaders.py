"""Utility loaders for file/stream inputs used by UI and CLI."""
from pypdf import PdfReader
import os
from typing import Union


def _read_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(stream=data)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.strip()


def extract_text_from_file(file_or_obj: Union[str, bytes, object]) -> str:
    """Accepts a filesystem path, raw bytes, or a streamlit UploadedFile-like object."""
    # If it's a path-like string
    if isinstance(file_or_obj, str):
        if not os.path.exists(file_or_obj):
            raise FileNotFoundError(f"File not found: {file_or_obj}")
        if file_or_obj.lower().endswith(".pdf"):
            return _read_pdf_bytes(open(file_or_obj, "rb").read())
        elif file_or_obj.lower().endswith(".txt"):
            with open(file_or_obj, "r", encoding="utf-8") as f:
                return f.read()
        else:
            raise ValueError("Unsupported file format. Use PDF or TXT.")

    # If it's a streamlit UploadedFile or any object with read/getbuffer
    if hasattr(file_or_obj, "getbuffer") or hasattr(file_or_obj, "read"):
        name = getattr(file_or_obj, "name", "upload")
        suffix = os.path.splitext(name)[1].lower()
        data = file_or_obj.getbuffer() if hasattr(file_or_obj, "getbuffer") else file_or_obj.read()
        if hasattr(file_or_obj, "seek"):
            try:
                file_or_obj.seek(0)
            except Exception:
                pass
        if suffix == ".pdf":
            return _read_pdf_bytes(bytes(data))
        elif suffix == ".txt" or suffix == "":
            return bytes(data).decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported file format: {suffix or 'unknown'}. Use PDF or TXT.")

    raise ValueError("Unsupported input type. Provide path, bytes, or UploadedFile-like object.")