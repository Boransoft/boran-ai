import json
import threading
from itertools import combinations
from pathlib import Path

from app.config import settings
from app.knowledge.relation_extractor import extract_relations
from app.knowledge.text_processing import extract_concepts


DEFAULT_RELATION = "co_occurs"


def _build_edge_key(source: str, relation: str, target: str) -> str:
    return f"{source}|||{relation}|||{target}"


def _parse_edge_key(raw_key: str) -> tuple[str, str, str]:
    parts = raw_key.split("|||")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], DEFAULT_RELATION, parts[1]
    return raw_key, DEFAULT_RELATION, raw_key


class KnowledgeGraphStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._graph: dict[str, dict[str, dict[str, int]]] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return

        with self.file_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        self._graph = data if isinstance(data, dict) else {}

    def _save(self) -> None:
        with self.file_path.open("w", encoding="utf-8") as fp:
            json.dump(self._graph, fp, ensure_ascii=False, indent=2)

    def _update_nodes(self, nodes: dict[str, int], concepts: list[str]) -> None:
        for concept in concepts:
            nodes[concept] = int(nodes.get(concept, 0)) + 1

    def _update_edges(
        self,
        edges: dict[str, int],
        concepts: list[str],
        extracted_relations: list[tuple[str, str, str]],
    ) -> None:
        used_pairs: set[tuple[str, str]] = set()

        for source, relation, target in extracted_relations:
            key = _build_edge_key(source, relation, target)
            edges[key] = int(edges.get(key, 0)) + 1
            used_pairs.add((source, target))
            used_pairs.add((target, source))

        for left, right in combinations(sorted(concepts), 2):
            if (left, right) in used_pairs or (right, left) in used_pairs:
                continue
            key = _build_edge_key(left, DEFAULT_RELATION, right)
            edges[key] = int(edges.get(key, 0)) + 1

    def update_from_text(self, user_id: str, text: str) -> None:
        concepts = extract_concepts(text)
        if len(concepts) < 2:
            return

        extracted_relations = extract_relations(text)

        with self._lock:
            graph = self._graph.setdefault(user_id, {"nodes": {}, "edges": {}})
            nodes = graph["nodes"]
            edges = graph["edges"]

            self._update_nodes(nodes, concepts)
            self._update_edges(edges, concepts, extracted_relations)
            self._save()

    def get_user_graph(
        self,
        user_id: str,
        max_nodes: int = 30,
        max_edges: int = 50,
    ) -> dict[str, list[dict[str, int | str]]]:
        graph = self._graph.get(user_id, {"nodes": {}, "edges": {}})
        sorted_nodes = sorted(
            graph["nodes"].items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
        sorted_edges = sorted(
            graph["edges"].items(),
            key=lambda pair: pair[1],
            reverse=True,
        )

        nodes = [{"id": name, "weight": weight} for name, weight in sorted_nodes[:max_nodes]]
        edges: list[dict[str, int | str]] = []
        for raw_key, weight in sorted_edges[:max_edges]:
            source, relation, target = _parse_edge_key(raw_key)
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "weight": weight,
                }
            )

        return {"nodes": nodes, "edges": edges}


knowledge_graph = KnowledgeGraphStore(Path(settings.graph_path) / "knowledge_graph.json")
