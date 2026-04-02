import shutil
from pathlib import Path

from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.consolidation import ConsolidationEngine
from app.learning.graph import LearningGraphStore
from app.learning.reflection import ReflectionEngine
from app.memory.long_term import LongTermMemoryStore


def test_consolidation_triggers_reflection_and_writes_summary():
    base = Path(".tmp") / "test_consolidation_triggers_reflection_and_writes_summary"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LongTermMemoryStore(base / "memory.jsonl")
        graph = LearningGraphStore(base / "learning_graph.json")
        reflection = ReflectionEngine(memory_store=store, graph_store=graph)
        engine = ConsolidationEngine(
            state_path=base / "state.json",
            memory_store=store,
            graph_store=graph,
            reflection=reflection,
            min_new_items=2,
        )

        store.add("u1", "Kullanici semantik arama kalitesini onemli goruyor", "semantic_conversation", "chat")
        store.add("u1", "Proje kapsaminda OCR pipeline gelistiriliyor", "semantic_document", "ingest")
        store.add(
            "u1",
            "Original answer: kisa cevap\nCorrected answer: Her zaman kaynaklari dogrula",
            "correction",
            "feedback",
        )
        graph.update_from_extraction(
            "u1",
            ExtractionResult(
                concepts=[
                    Concept(term="semantic search", kind="term", score=0.9, frequency=3),
                    Concept(term="ocr", kind="term", score=0.8, frequency=2),
                ],
                relations=[
                    Relation(source="semantic search", relation="uses", target="ocr", weight=2),
                ],
            ),
        )

        result = engine.run_for_user("u1")
        assert result["status"] == "ok"
        assert int(result["summary_created"]) >= 1
        assert int(result["reflections_created"]) >= 1

        kinds = {str(item.get("kind")) for item in store.list_user("u1", limit=50)}
        assert "recent_learning_summary" in kinds

        all_users_result = engine.run_for_all_users()
        assert int(all_users_result["processed_users"]) >= 1
    finally:
        shutil.rmtree(base, ignore_errors=True)
