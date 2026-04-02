from app.learning.extractor import concept_extractor


def test_concept_extractor_returns_concepts_and_relations():
    text = "Python uses ChromaDB for semantic search. Boran AI improves memory quality."
    result = concept_extractor.extract(text)

    terms = {item.term for item in result.concepts}
    assert "python" in terms
    assert "chromadb" in terms
    assert any(rel.relation == "uses" for rel in result.relations)
