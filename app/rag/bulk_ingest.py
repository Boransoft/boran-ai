from app.config import settings
from app.ingest.service import ingest_folder_unified


def ingest_folder(folder_path: str | None = None) -> list[dict[str, object]]:
    target_folder = folder_path or settings.pdf_path
    return ingest_folder_unified(folder_path=target_folder, category="pdf")
