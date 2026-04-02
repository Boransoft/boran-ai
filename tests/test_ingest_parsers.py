import json
import shutil
from pathlib import Path

from app.ingest.parsers import parse_file_to_text


def test_parse_csv_dataset():
    base = Path(".tmp") / "test_parse_csv_dataset"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        file_path = base / "sample.csv"
        file_path.write_text("name,score\nali,10\nayse,20\n", encoding="utf-8")
        text, method, content_type = parse_file_to_text(str(file_path))
        assert "ali" in text
        assert method == "dataset_preview"
        assert content_type == "dataset"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_parse_jsonl_dataset():
    base = Path(".tmp") / "test_parse_jsonl_dataset"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        file_path = base / "sample.jsonl"
        rows = [{"k": "v1"}, {"k": "v2"}]
        file_path.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
        text, method, content_type = parse_file_to_text(str(file_path))
        assert "v1" in text
        assert method == "dataset_preview"
        assert content_type == "dataset"
    finally:
        shutil.rmtree(base, ignore_errors=True)
