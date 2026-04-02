import shutil
from pathlib import Path

from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.graph import LearningGraphStore
from app.learning.reflection import ReflectionEngine
from app.memory.long_term import LongTermMemoryStore


def _seed_user_data(store: LongTermMemoryStore, graph: LearningGraphStore, user_id: str, marker: str) -> None:
    store.add(
        user_id,
        f"Kullanici {marker} tarafinda kaynak temelli yanitlari tercih ediyor.",
        "semantic_conversation",
        "chat",
    )
    store.add(
        user_id,
        f"{marker} projesinde knowledge graph ve retrieval pipeline var.",
        "semantic_document",
        "ingest",
        metadata={"category": "research"},
    )
    store.add(
        user_id,
        "Original answer: varsayim\nCorrected answer: Her zaman kullanici duzeltmesini oncele",
        "correction",
        "feedback",
    )
    graph.update_from_extraction(
        user_id,
        ExtractionResult(
            concepts=[
                Concept(term=f"{marker}_topic", kind="term", score=0.9, frequency=3),
                Concept(term="retrieval", kind="term", score=0.8, frequency=2),
            ],
            relations=[
                Relation(source=f"{marker}_topic", relation="uses", target="retrieval", weight=2),
            ],
        ),
    )


def test_reflection_generates_consolidated_memory_items():
    base = Path(".tmp") / "test_reflection_generates_consolidated_memory_items"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LongTermMemoryStore(base / "memory.jsonl")
        graph = LearningGraphStore(base / "learning_graph.json")
        engine = ReflectionEngine(memory_store=store, graph_store=graph)

        _seed_user_data(store, graph, "u1", "alpha")

        result = engine.reflect_user(user_id="u1", persist=True)
        assert result["status"] == "ok"
        assert int(result["stored_count"]) >= 1

        kinds = {str(item.get("kind")) for item in engine.list_reflections(user_id="u1", limit=30)}
        assert "recent_learning_summary" in kinds
        assert "user_preferences" in kinds
        assert "stable_rules" in kinds
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_reflection_user_isolation():
    base = Path(".tmp") / "test_reflection_user_isolation"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LongTermMemoryStore(base / "memory.jsonl")
        graph = LearningGraphStore(base / "learning_graph.json")
        engine = ReflectionEngine(memory_store=store, graph_store=graph)

        _seed_user_data(store, graph, "u1", "alpha")
        _seed_user_data(store, graph, "u2", "beta")

        engine.reflect_user(user_id="u1", persist=True)
        engine.reflect_user(user_id="u2", persist=True)

        summary_u1 = engine.get_summary(user_id="u1")
        summary_u2 = engine.get_summary(user_id="u2")

        u1_text = " ".join(str(summary_u1.get(key, "")) for key in summary_u1)
        u2_text = " ".join(str(summary_u2.get(key, "")) for key in summary_u2)
        assert "alpha_topic" in u1_text
        assert "beta_topic" not in u1_text
        assert "beta_topic" in u2_text
        assert "alpha_topic" not in u2_text
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_reflection_summary_generation_contains_preferences_and_rules():
    base = Path(".tmp") / "test_reflection_summary_generation_contains_preferences_and_rules"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LongTermMemoryStore(base / "memory.jsonl")
        graph = LearningGraphStore(base / "learning_graph.json")
        engine = ReflectionEngine(memory_store=store, graph_store=graph)

        _seed_user_data(store, graph, "u1", "gamma")
        engine.reflect_user(user_id="u1", persist=True)

        summary = engine.get_summary(user_id="u1")
        assert summary["summary"]
        assert "Kullanici tercihleri" in summary["user_preferences"]
        assert "Kalici kurallar" in summary["stable_rules"]
    finally:
        shutil.rmtree(base, ignore_errors=True)
