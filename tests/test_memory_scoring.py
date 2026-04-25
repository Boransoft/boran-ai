import shutil
from pathlib import Path

from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.graph import LearningGraphStore
from app.learning.scoring import MemoryScoringEngine
from app.memory.long_term import LongTermMemoryStore


class _StubClusterEngine:
    def list_clusters(self, user_id: str, limit: int = 30):
        if user_id == "u1":
            return [
                {
                    "cluster_id": "u1:c1",
                    "label": "ihale ve yazisma",
                    "size": 2,
                    "score": 2.0,
                    "terms": ["ihale", "yazisma"],
                }
            ]
        return []


class _StubReflection:
    def get_summary(self, user_id: str):
        if user_id == "u1":
            return {
                "summary": "kullanici ihaleyi onemli goruyor",
                "user_preferences": "onemli teknik detaylar",
                "stable_rules": "",
                "project_focus": "",
            }
        return {
            "summary": "",
            "user_preferences": "",
            "stable_rules": "",
            "project_focus": "",
        }


def test_memory_scoring_prioritizes_important_items_and_user_isolation():
    base = Path(".tmp") / "test_memory_scoring_prioritizes_important_items_and_user_isolation"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        memory_store = LongTermMemoryStore(base / "memory.jsonl")
        graph_store = LearningGraphStore(base / "graph.json")

        graph_store.update_from_extraction(
            "u1",
            ExtractionResult(
                concepts=[
                    Concept(term="ihale", kind="term", score=1.0, frequency=3),
                    Concept(term="yazisma", kind="term", score=1.0, frequency=2),
                ],
                relations=[
                    Relation(source="ihale", relation="requires", target="yazisma", weight=3),
                ],
            ),
        )

        memory_store.add(
            user_id="u1",
            text="Bunu hatirla: ihale dosyasindaki yazisma akisi cok onemli.",
            kind="semantic_conversation",
            source="chat",
        )
        memory_store.add(
            user_id="u1",
            text="genel not",
            kind="semantic_conversation",
            source="chat",
        )
        memory_store.add(
            user_id="u2",
            text="u2 secret memory",
            kind="semantic_conversation",
            source="chat",
        )

        engine = MemoryScoringEngine(
            memory_store=memory_store,
            graph_store=graph_store,
            cluster_engine=_StubClusterEngine(),
            reflection=_StubReflection(),
        )

        top_u1 = engine.top_memories(user_id="u1", query="ihale", limit=5)
        assert top_u1
        assert "onemli" in str(top_u1[0]["text"]).lower()
        assert all(str(item["user_id"]) == "u1" for item in top_u1)

        top_u2 = engine.top_memories(user_id="u2", query="secret", limit=5)
        assert top_u2
        assert all(str(item["user_id"]) == "u2" for item in top_u2)
    finally:
        shutil.rmtree(base, ignore_errors=True)

