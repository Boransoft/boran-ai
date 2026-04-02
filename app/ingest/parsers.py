import csv
import json
from pathlib import Path

from PIL import Image
from docx import Document
import pytesseract

from app.config import settings
from app.rag.ingest import extract_text_from_pdf
from app.rag.ocr_utils import extract_text_with_ocr


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".jsonl",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
}


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
DATASET_EXTENSIONS = {".csv", ".json", ".jsonl"}


def _read_text_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


def _parse_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    lines = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    return "\n".join(lines).strip()


def _parse_doc(file_path: Path) -> str:
    # Legacy DOC extraction is environment-dependent. We keep a best-effort fallback.
    return _read_text_file(file_path)


def _parse_csv(file_path: Path, max_rows: int) -> str:
    output: list[str] = []
    with file_path.open("r", encoding="utf-8", errors="ignore", newline="") as fp:
        reader = csv.reader(fp)
        for index, row in enumerate(reader):
            if index >= max_rows:
                break
            output.append(" | ".join(cell.strip() for cell in row))
    return "\n".join(output).strip()


def _parse_json(file_path: Path, max_rows: int) -> str:
    data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    if isinstance(data, list):
        rows = data[:max_rows]
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in rows)
    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False)
    return str(data)


def _parse_jsonl(file_path: Path, max_rows: int) -> str:
    output: list[str] = []
    with file_path.open("r", encoding="utf-8", errors="ignore") as fp:
        for index, line in enumerate(fp):
            if index >= max_rows:
                break
            line = line.strip()
            if line:
                output.append(line)
    return "\n".join(output).strip()


def _parse_dataset(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".csv":
        return _parse_csv(file_path, max_rows=settings.dataset_preview_rows)
    if ext == ".json":
        return _parse_json(file_path, max_rows=settings.dataset_preview_rows)
    if ext == ".jsonl":
        return _parse_jsonl(file_path, max_rows=settings.dataset_preview_rows)
    return _read_text_file(file_path)


def _parse_image(file_path: Path) -> str:
    image = Image.open(file_path)
    return pytesseract.image_to_string(image, lang="eng+tur").strip()


def parse_file_to_text(file_path: str) -> tuple[str, str, str]:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")

    if ext == ".pdf":
        text = extract_text_from_pdf(str(path))
        method = "normal"
        if not text:
            text = extract_text_with_ocr(str(path))
            method = "ocr"
        return text, method, "pdf"

    if ext == ".docx":
        return _parse_docx(path), "normal", "docx"

    if ext == ".doc":
        return _parse_doc(path), "best_effort", "doc"

    if ext in IMAGE_EXTENSIONS:
        return _parse_image(path), "ocr", "image"

    if ext in DATASET_EXTENSIONS:
        return _parse_dataset(path), "dataset_preview", "dataset"

    return _read_text_file(path), "normal", "text"
