import shutil
from pathlib import Path

from app.learning.clustering import ConceptClusterEngine
from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.graph import LearningGraphStore
from app.memory.long_term import LongTermMemoryStore


def test_cluster_generation_and_persistence():
    base = Path(".tmp") / "test_cluster_generation_and_persistence"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        graph_store = LearningGraphStore(base / "graph.json")
        memory_store = LongTermMemoryStore(base / "memory.jsonl")
        engine = ConceptClusterEngine(graph_store=graph_store, memory_store=memory_store)

        graph_store.update_from_extraction(
            "u1",
            ExtractionResult(
                concepts=[
                    Concept(term="ihale", kind="term", score=1.0, frequency=3),
                    Concept(term="tender", kind="term", score=1.0, frequency=3),
                    Concept(term="yazisma", kind="term", score=1.0, frequency=2),
                ],
                relations=[
                    Relation(source="ihale", relation="related_to", target="tender", weight=3),
                    Relation(source="ihale", relation="requires", target="yazisma", weight=2),
                ],
            ),
        )

        clusters = engine.build_clusters(user_id="u1")
        assert clusters
        assert clusters[0]["size"] >= 2
        assert "ve" in clusters[0]["label"] or len(clusters[0]["terms"]) >= 2

        persisted = engine.persist_clusters(user_id="u1", clusters=clusters)
        assert persisted >= 1

        listed = engine.list_clusters(user_id="u1", limit=10)
        assert listed
        assert listed[0]["label"]
    finally:
        shutil.rmtree(base, ignore_errors=True)

