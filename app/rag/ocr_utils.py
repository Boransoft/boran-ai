# pyright: reportMissingImports=false

from pdf2image import convert_from_path
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_with_ocr(pdf_path: str) -> str:
    pages = convert_from_path(pdf_path)
    full_text = []

    for page in pages:
        text = pytesseract.image_to_string(page)
        if text and text.strip():
            full_text.append(text)

    return "\n".join(full_text).strip()