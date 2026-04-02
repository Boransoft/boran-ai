import shutil
from pathlib import Path

from app.memory.long_term import LongTermMemoryStore


def test_long_term_memory_add_and_search():
    base_temp = Path(".tmp")
    base_temp.mkdir(parents=True, exist_ok=True)
    temp_dir = base_temp / "test_long_term_memory"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        store = LongTermMemoryStore(temp_dir / "memory.jsonl")

        store.add(
            user_id="u1",
            text="User likes semantic search with vector db",
            kind="fact",
            source="chat",
        )
        store.add(
            user_id="u1",
            text="OCR is useful for scanned PDF files",
            kind="fact",
            source="chat",
        )

        results = store.search(user_id="u1", query="vector search", limit=2)

        assert len(results) == 1
        assert "vector db" in str(results[0]["text"])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
