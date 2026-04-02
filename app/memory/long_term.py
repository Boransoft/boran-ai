import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


class LongTermMemoryStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._items: list[dict[str, object]] = []
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return

        with self.file_path.open("r", encoding="utf-8") as fp:
            for raw_line in fp:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                self._items.append(json.loads(raw_line))

    def _append_to_disk(self, item: dict[str, object]) -> None:
        with self.file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")

    def add(
        self,
        user_id: str,
        text: str,
        kind: str,
        source: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if not text.strip():
            return ""

        item = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "kind": kind,
            "text": text.strip(),
            "source": source,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        with self._lock:
            self._items.append(item)
            self._append_to_disk(item)

        return str(item["id"])

    def list_user(self, user_id: str, limit: int = 50) -> list[dict[str, object]]:
        matches = [x for x in self._items if x.get("user_id") == user_id]
        matches.sort(key=lambda x: str(x.get("created_at")), reverse=True)
        return matches[:limit]

    def get_user_ids(self) -> list[str]:
        ids = {str(item.get("user_id")) for item in self._items if item.get("user_id")}
        return sorted(ids)

    def all_items(self) -> list[dict[str, object]]:
        return list(self._items)

    def search(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, object]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, dict[str, object]]] = []
        for item in self._items:
            if item.get("user_id") != user_id:
                continue
            tokens = _tokenize(str(item.get("text", "")))
            score = len(tokens.intersection(query_tokens))
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]


long_term_memory = LongTermMemoryStore(
    Path(settings.memory_path) / "long_term_memory.jsonl"
)
