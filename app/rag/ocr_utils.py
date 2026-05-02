import logging
from typing import Any

logger = logging.getLogger("uvicorn.error")

def ocr_unavailable_warning() -> str:
    return "OCR disabled."


def is_pdf_ocr_available() -> bool:
    return False


def is_image_ocr_available() -> bool:
    return False


def has_opencv() -> bool:
    return False


def extract_text_with_ocr(pdf_path: str, language: str = "eng+tur") -> str:
    logger.info("ocr_pdf_bypassed file=%s", pdf_path)
    return ""


def extract_text_from_image_with_ocr(image: Any, language: str = "eng+tur") -> str:
    logger.info("ocr_image_bypassed")
    return ""


def ocr_pdf(pdf_path: str, language: str = "eng+tur") -> str:
    return ""


def ocr_image(image: Any, language: str = "eng+tur") -> str:
    return ""


def parse_pdf(pdf_path: str, language: str = "eng+tur") -> str:
    return ""
