import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.learning.reflection import REFLECTION_KINDS, ReflectionEngine, reflection_engine
from app.learning.graph import learning_graph_store
from app.memory.long_term import LongTermMemoryStore, long_term_memory


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class ConsolidationEngine:
    def __init__(
        self,
        state_path: Path,
        memory_store: LongTermMemoryStore = long_term_memory,
        graph_store=None,
        reflection: ReflectionEngine | None = None,
        min_new_items: int | None = None,
    ):
        self.state_path = state_path
        self.memory_store = memory_store
        self.graph_store = graph_store or learning_graph_store
        self.reflection = reflection or ReflectionEngine(
            memory_store=memory_store,
            graph_store=self.graph_store,
        )
        self.min_new_items = min_new_items or settings.consolidation_min_new_items
        self._lock = threading.Lock()
        self._state: dict[str, str] = {}
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        with self.state_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        self._state = data if isinstance(data, dict) else {}

    def _save_state(self) -> None:
        with self.state_path.open("w", encoding="utf-8") as fp:
            json.dump(self._state, fp, ensure_ascii=False, indent=2)

    def get_state(self) -> dict[str, str]:
        with self._lock:
            return dict(self._state)

    def _new_signal_items_for_user(self, user_id: str) -> list[dict[str, object]]:
        items = self.memory_store.list_user(user_id=user_id, limit=5000)
        items = [item for item in items if str(item.get("kind")) not in REFLECTION_KINDS]
        items.sort(key=lambda item: str(item.get("created_at")))

        last_ts = self._state.get(user_id)
        if not last_ts:
            return items

        last_dt = _parse_iso(last_ts)
        return [
            item
            for item in items
            if item.get("created_at") and _parse_iso(str(item["created_at"])) > last_dt
        ]

    def run_for_user(self, user_id: str, force: bool = False) -> dict[str, object]:
        with self._lock:
            new_items = self._new_signal_items_for_user(user_id=user_id)
            if not force and len(new_items) < self.min_new_items:
                return {
                    "status": "skipped",
                    "user_id": user_id,
                    "new_items": len(new_items),
                    "summary_created": 0,
                    "reflections_created": 0,
                }

            reflection_result = self.reflection.reflect_user(user_id=user_id, persist=True)
            generated = reflection_result.get("generated", {})
            stored_count = int(reflection_result.get("stored_count", 0))

            latest_ts = (
                str(new_items[-1].get("created_at"))
                if new_items
                else datetime.now(tz=timezone.utc).isoformat()
            )
            self._state[user_id] = latest_ts
            self._save_state()

            summary_created = 1 if generated.get("recent_learning_summary") and stored_count > 0 else 0
            return {
                "status": "ok",
                "user_id": user_id,
                "new_items": len(new_items),
                "summary_created": summary_created,
                "reflections_created": stored_count,
            }

    def run_for_all_users(self) -> dict[str, object]:
        user_ids = set(self.memory_store.get_user_ids())
        if self.graph_store and hasattr(self.graph_store, "get_user_ids"):
            try:
                user_ids.update(self.graph_store.get_user_ids())
            except Exception:
                pass

        summaries_created = 0
        reflections_created = 0

        for user_id in sorted(user_ids):
            result = self.run_for_user(user_id=user_id)
            summaries_created += int(result.get("summary_created", 0))
            reflections_created += int(result.get("reflections_created", 0))

        return {
            "status": "ok",
            "processed_users": len(user_ids),
            "summaries_created": summaries_created,
            "reflections_created": reflections_created,
        }


consolidation_engine = ConsolidationEngine(
    state_path=Path(settings.memory_path) / "consolidation_state.json",
    graph_store=reflection_engine.graph_store,
)
