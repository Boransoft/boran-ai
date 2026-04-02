from pdf2image import convert_from_path
import pytesseract

from app.config import settings

if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text_with_ocr(pdf_path: str, language: str = "eng+tur") -> str:
    pages = convert_from_path(pdf_path)
    full_text = []

    for page in pages:
        text = pytesseract.image_to_string(page, lang=language)
        if text and text.strip():
            full_text.append(text)

    return "\n".join(full_text).strip()
