import shutil
from pathlib import Path

from app.learning.concepts import Concept, ExtractionResult, Relation
from app.learning.graph import LearningGraphStore
from app.learning.graph_relations import merge_relations


def test_graph_relation_merge_and_weight_accumulation():
    merged = merge_relations(
        [
            Relation(source="Tender", relation="related_to", target="Ihale", weight=1),
            Relation(source="ihale", relation="related_to", target="tender", weight=2),
        ]
    )
    assert len(merged) == 1
    assert merged[0].source == "ihale"
    assert merged[0].target == "tender"
    assert merged[0].weight == 3

    base = Path(".tmp") / "test_graph_relation_merge_and_weight_accumulation"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = LearningGraphStore(base / "learning_graph.json")
        result = ExtractionResult(
            concepts=[
                Concept(term="ihale", kind="term", frequency=1, score=0.9),
                Concept(term="tender", kind="term", frequency=1, score=0.9),
            ],
            relations=merged,
        )
        store.update_from_extraction("u1", result)
        store.update_from_extraction("u1", result)

        graph = store.get_graph("u1", max_nodes=20, max_edges=20)
        edges = [edge for edge in graph["edges"] if edge["relation"] == "related_to"]
        assert len(edges) == 1
        assert int(edges[0]["weight"]) == 6
        assert int(edges[0]["frequency"]) >= 2
    finally:
        shutil.rmtree(base, ignore_errors=True)

