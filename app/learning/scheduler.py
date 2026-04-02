import threading

from app.config import settings
from app.learning.consolidation import consolidation_engine


class ConsolidationScheduler:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                consolidation_engine.run_for_all_users()
            except Exception as exc:
                print(f"Consolidation scheduler error: {exc}")
            self._stop_event.wait(timeout=settings.consolidation_interval_seconds)

    def start(self) -> None:
        if not settings.auto_consolidation_enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None


consolidation_scheduler = ConsolidationScheduler()
