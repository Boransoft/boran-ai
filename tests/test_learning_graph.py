import shutil
from pathlib import Path

from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.graph import LearningGraphStore


def _make_result() -> ExtractionResult:
    return ExtractionResult(
        concepts=[
            Concept(term="python", kind="term", score=0.8, frequency=2),
            Concept(term="chromadb", kind="term", score=0.7, frequency=1),
        ],
        relations=[
            Relation(source="python", relation="uses", target="chromadb", weight=1),
        ],
    )


def test_learning_graph_updates_frequency_and_edges():
    base = Path(".tmp") / "test_learning_graph_updates_frequency_and_edges"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LearningGraphStore(base / "learning_graph.json")
        store.update_from_extraction("u1", _make_result())
        store.update_from_extraction("u1", _make_result())

        concepts = store.get_concepts("u1", limit=10)
        graph = store.get_graph("u1", max_nodes=10, max_edges=10)

        python = next(item for item in concepts if item["term"] == "python")
        assert int(python["frequency"]) >= 4
        assert any(edge["relation"] == "uses" and edge["weight"] >= 2 for edge in graph["edges"])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_learning_graph_user_isolation():
    base = Path(".tmp") / "test_learning_graph_user_isolation"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LearningGraphStore(base / "learning_graph.json")
        store.update_from_extraction(
            "u1",
            ExtractionResult(
                concepts=[Concept(term="alpha", kind="term", score=0.9, frequency=1)],
                relations=[],
            ),
        )
        store.update_from_extraction(
            "u2",
            ExtractionResult(
                concepts=[Concept(term="beta", kind="term", score=0.9, frequency=1)],
                relations=[],
            ),
        )

        u1_terms = {item["term"] for item in store.get_concepts("u1", limit=10)}
        u2_terms = {item["term"] for item in store.get_concepts("u2", limit=10)}
        assert "alpha" in u1_terms and "beta" not in u1_terms
        assert "beta" in u2_terms and "alpha" not in u2_terms
    finally:
        shutil.rmtree(base, ignore_errors=True)
