import logging
from typing import Any

from app.config import settings

logger = logging.getLogger("uvicorn.error")

try:
    import pytesseract as _pytesseract
except Exception as exc:  # pragma: no cover - environment-dependent optional dependency
    logger.warning("optional_dependency_unavailable name=pytesseract error=%s", exc)
    _pytesseract = None

try:
    from pdf2image import convert_from_path as _convert_from_path
except Exception as exc:  # pragma: no cover - environment-dependent optional dependency
    logger.warning("optional_dependency_unavailable name=pdf2image error=%s", exc)
    _convert_from_path = None

try:
    import cv2 as _cv2
except Exception as exc:  # pragma: no cover - environment-dependent optional dependency
    logger.warning("optional_dependency_unavailable name=cv2 error=%s", exc)
    _cv2 = None

if _pytesseract is not None and settings.tesseract_cmd:
    try:
        _pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    except Exception as exc:  # pragma: no cover - environment-dependent optional dependency
        logger.warning("tesseract_cmd_config_failed error=%s", exc)


def ocr_unavailable_warning() -> str:
    missing: list[str] = []
    if _pytesseract is None:
        missing.append("pytesseract")
    if _convert_from_path is None:
        missing.append("pdf2image")
    if missing:
        return "OCR unavailable: missing optional dependencies: " + ", ".join(missing) + "."
    return "OCR unavailable in this environment."


def is_pdf_ocr_available() -> bool:
    return _pytesseract is not None and _convert_from_path is not None


def is_image_ocr_available() -> bool:
    return _pytesseract is not None


def has_opencv() -> bool:
    return _cv2 is not None


def extract_text_with_ocr(pdf_path: str, language: str = "eng+tur") -> str:
    if not is_pdf_ocr_available():
        logger.warning("ocr_pdf_skipped reason=%s", ocr_unavailable_warning())
        return ""

    assert _convert_from_path is not None
    assert _pytesseract is not None

    try:
        pages = _convert_from_path(pdf_path)
    except Exception as exc:
        logger.warning("ocr_pdf_convert_failed file=%s error=%s", pdf_path, exc)
        return ""

    full_text: list[str] = []
    for page in pages:
        try:
            text = _pytesseract.image_to_string(page, lang=language)
        except Exception as exc:
            logger.warning("ocr_page_extract_failed file=%s error=%s", pdf_path, exc)
            continue
        if text and text.strip():
            full_text.append(text)

    return "\n".join(full_text).strip()


def extract_text_from_image_with_ocr(image: Any, language: str = "eng+tur") -> str:
    if not is_image_ocr_available():
        logger.warning("ocr_image_skipped reason=%s", ocr_unavailable_warning())
        return ""

    assert _pytesseract is not None
    try:
        return _pytesseract.image_to_string(image, lang=language).strip()
    except Exception as exc:
        logger.warning("ocr_image_extract_failed error=%s", exc)
        return ""
