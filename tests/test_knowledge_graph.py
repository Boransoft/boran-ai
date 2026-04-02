import shutil
from pathlib import Path

from app.knowledge.graph import KnowledgeGraphStore
from app.knowledge.relation_extractor import extract_relations


def test_knowledge_graph_updates_nodes_and_edges():
    base_temp = Path(".tmp")
    base_temp.mkdir(parents=True, exist_ok=True)
    temp_dir = base_temp / "test_knowledge_graph"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        graph = KnowledgeGraphStore(temp_dir / "graph.json")
        graph.update_from_text("u1", "Python vector database semantic search")
        graph.update_from_text("u1", "Python semantic memory graph")

        result = graph.get_user_graph("u1")
        node_ids = {node["id"] for node in result["nodes"]}

        assert "python" in node_ids
        assert "semantic" in node_ids
        assert len(result["edges"]) > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_relation_extraction_adds_typed_edges():
    base_temp = Path(".tmp")
    base_temp.mkdir(parents=True, exist_ok=True)
    temp_dir = base_temp / "test_knowledge_graph_relations"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        graph = KnowledgeGraphStore(temp_dir / "graph.json")
        graph.update_from_text("u2", "Python uses ChromaDB for semantic search.")

        result = graph.get_user_graph("u2")
        typed_edges = [edge for edge in result["edges"] if edge.get("relation") == "uses"]

        assert len(typed_edges) >= 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_relation_extractor_detects_keyword_relations():
    triples = extract_relations("Retriever requires vector database for semantic search.")

    assert any(triple[1] == "requires" for triple in triples)
