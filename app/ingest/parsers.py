import csv
import json
import logging
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from PIL import Image
from docx import Document
from pypdf import PdfReader

from app.config import settings

logger = logging.getLogger("uvicorn.error")


class _OCRUtilsModule(Protocol):
    def extract_text_from_image_with_ocr(self, image: Image.Image, language: str = "eng+tur") -> str: ...
    def extract_text_with_ocr(self, pdf_path: str, language: str = "eng+tur") -> str: ...
    def is_image_ocr_available(self) -> bool: ...
    def is_pdf_ocr_available(self) -> bool: ...


_OCR_UTILS_MODULE: _OCRUtilsModule | None = None
_OCR_UTILS_LOAD_FAILED = False


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
    ".webp",
    ".tiff",
    ".bmp",
}


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}
DATASET_EXTENSIONS = {".csv", ".json", ".jsonl"}


def _load_ocr_utils() -> _OCRUtilsModule | None:
    global _OCR_UTILS_MODULE, _OCR_UTILS_LOAD_FAILED

    if _OCR_UTILS_MODULE is not None:
        return _OCR_UTILS_MODULE
    if _OCR_UTILS_LOAD_FAILED:
        return None

    try:
        module = import_module("app.rag.ocr_utils")
    except Exception as exc:
        logger.warning("ocr_utils_import_failed error=%s", exc)
        _OCR_UTILS_LOAD_FAILED = True
        return None

    _OCR_UTILS_MODULE = cast(_OCRUtilsModule, module)
    return _OCR_UTILS_MODULE


def _read_text_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


def _parse_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    lines = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    return "\n".join(lines).strip()


def _parse_doc(file_path: Path) -> str:
    # Legacy DOC extraction is environment-dependent. We keep a best-effort fallback.
    return _read_text_file(file_path)


def _extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    full_text: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text.append(page_text)
    return "\n".join(full_text).strip()


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


def _parse_image(file_path: Path, ocr_utils: _OCRUtilsModule | None = None) -> str:
    if ocr_utils is None:
        ocr_utils = _load_ocr_utils()
    if ocr_utils is None:
        return ""
    with Image.open(file_path) as image:
        return ocr_utils.extract_text_from_image_with_ocr(image, language="eng+tur")


def parse_file_to_text(file_path: str) -> tuple[str, str, str]:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")

    if ext == ".pdf":
        text = _extract_text_from_pdf(path)
        method = "normal"
        if not text:
            ocr_utils = _load_ocr_utils()
            if ocr_utils is None or not ocr_utils.is_pdf_ocr_available():
                return "", "ocr_unavailable", "pdf"
            text = ocr_utils.extract_text_with_ocr(str(path))
            method = "ocr"
        return text, method, "pdf"

    if ext == ".docx":
        return _parse_docx(path), "normal", "docx"

    if ext == ".doc":
        return _parse_doc(path), "best_effort", "doc"

    if ext in IMAGE_EXTENSIONS:
        ocr_utils = _load_ocr_utils()
        text = _parse_image(path, ocr_utils=ocr_utils)
        method = "ocr"
        if not text and (ocr_utils is None or not ocr_utils.is_image_ocr_available()):
            method = "ocr_unavailable"
        return text, method, "image"

    if ext in DATASET_EXTENSIONS:
        return _parse_dataset(path), "dataset_preview", "dataset"

    return _read_text_file(path), "normal", "text"
