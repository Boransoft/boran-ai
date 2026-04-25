from app.config import settings
from app.learning.semantic_linking import SemanticLinker


class _StubGraphStore:
    def __init__(self):
        self._data = {
            "u1": ["ihale", "tender", "muayene", "acceptance"],
            "u2": ["voice", "assistant"],
        }

    def get_concepts(self, user_id: str, limit: int = 100):
        terms = self._data.get(user_id, [])[:limit]
        return [{"term": term, "kind": "term", "score": 1.0, "frequency": 1} for term in terms]


def _fake_embedder(texts: list[str]) -> list[list[float]]:
    vectors = {
        "ihale": [1.0, 0.0, 0.0],
        "tender": [0.95, 0.1, 0.0],
        "muayene": [0.0, 1.0, 0.0],
        "acceptance": [0.0, 0.92, 0.08],
        "voice": [0.0, 0.0, 1.0],
        "assistant": [0.0, 0.05, 0.95],
        "dua": [0.2, 0.2, 0.9],
    }
    return [vectors.get(text, [0.33, 0.33, 0.33]) for text in texts]


def test_semantic_link_threshold_and_lookup():
    original_threshold = settings.semantic_link_threshold
    settings.semantic_link_threshold = 0.82
    try:
        linker = SemanticLinker(graph_store=_StubGraphStore(), embedder=_fake_embedder)

        relations = linker.build_semantic_relations(
            user_id="u1",
            terms=["ihale", "tender", "dua"],
        )
        triples = {(item.source, item.relation, item.target) for item in relations}

        assert ("ihale", "semantically_related", "tender") in triples
        assert all(
            not ({triple[0], triple[2]} == {"dua", "ihale"})
            for triple in triples
        )

        related_for_u1 = linker.lookup_similar_terms(user_id="u1", term="ihale", limit=5)
        assert any(item["term"] == "tender" for item in related_for_u1)
        assert all(item["term"] != "voice" for item in related_for_u1)
    finally:
        settings.semantic_link_threshold = original_threshold

