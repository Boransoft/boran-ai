import os
from app.rag.ingest import ingest_pdf


def ingest_folder(folder_path: str = "data/pdf"):
    results = []

    if not os.path.exists(folder_path):
        return [{
            "status": "error",
            "file": folder_path,
            "message": "Klasör bulunamadı."
        }]

    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".pdf"):
            full_path = os.path.join(folder_path, file_name)
            result = ingest_pdf(full_path)
            results.append(result)

    return results