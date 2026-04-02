import json
import threading
from collections import defaultdict
from pathlib import Path

from sqlalchemy import and_, select

from app.config import settings
from app.db.models import KnowledgeEdge, MemoryItem, User
from app.db.session import get_session
from app.learning.concepts import Concept, ExtractionResult, Relation, normalize_term


def _edge_key(source: str, relation: str, target: str) -> str:
    return f"{source}|||{relation}|||{target}"


def _parse_edge_key(value: str) -> tuple[str, str, str]:
    parts = value.split("|||")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], "co_occurs", parts[1]
    return value, "co_occurs", value


class LearningGraphStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, dict[str, dict[str, object] | int]]] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        with self.file_path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        self._data = payload if isinstance(payload, dict) else {}

    def _save(self) -> None:
        with self.file_path.open("w", encoding="utf-8") as fp:
            json.dump(self._data, fp, ensure_ascii=False, indent=2)

    def _ensure_user_graph(self, user_id: str) -> dict[str, dict[str, dict[str, object] | int]]:
        return self._data.setdefault(user_id, {"concepts": {}, "edges": {}})

    def _db_sync_enabled(self) -> bool:
        return bool(settings.database_url)

    def get_user_ids(self) -> list[str]:
        return sorted(self._data.keys())

    def _get_or_create_user_db_id(self, external_id: str) -> str | None:
        if not self._db_sync_enabled():
            return None
        with get_session() as session:
            user = session.execute(
                select(User).where(User.external_id == external_id)
            ).scalar_one_or_none()
            if user:
                return str(user.id)
            user = User(external_id=external_id, is_active=True)
            session.add(user)
            session.commit()
            session.refresh(user)
            return str(user.id)

    def _sync_concepts_to_db(self, user_id: str, concepts: list[Concept]) -> None:
        user_db_id = self._get_or_create_user_db_id(user_id)
        if not user_db_id:
            return

        with get_session() as session:
            for concept in concepts:
                existing = session.execute(
                    select(MemoryItem).where(
                        and_(
                            MemoryItem.user_id == user_db_id,
                            MemoryItem.kind == "concept",
                            MemoryItem.text == concept.term,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    meta = existing.metadata_json if isinstance(existing.metadata_json, dict) else {}
                    current_freq = int(meta.get("frequency", 0))
                    meta.update(
                        {
                            "kind": concept.kind,
                            "score": str(concept.score),
                            "frequency": str(current_freq + concept.frequency),
                        }
                    )
                    existing.metadata_json = meta
                else:
                    session.add(
                        MemoryItem(
                            user_id=user_db_id,
                            kind="concept",
                            text=concept.term,
                            source="learning_extractor",
                            metadata_json={
                                "kind": concept.kind,
                                "score": str(concept.score),
                                "frequency": str(concept.frequency),
                            },
                        )
                    )
            session.commit()

    def _sync_relations_to_db(self, user_id: str, relations: list[Relation]) -> None:
        user_db_id = self._get_or_create_user_db_id(user_id)
        if not user_db_id:
            return

        with get_session() as session:
            for relation in relations:
                existing = session.execute(
                    select(KnowledgeEdge).where(
                        and_(
                            KnowledgeEdge.user_id == user_db_id,
                            KnowledgeEdge.source_node == relation.source,
                            KnowledgeEdge.relation == relation.relation,
                            KnowledgeEdge.target_node == relation.target,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.weight = int(existing.weight) + int(relation.weight)
                else:
                    session.add(
                        KnowledgeEdge(
                            user_id=user_db_id,
                            source_node=relation.source,
                            relation=relation.relation,
                            target_node=relation.target,
                            weight=int(relation.weight),
                            metadata_json={},
                        )
                    )
            session.commit()

    def update_from_extraction(self, user_id: str, result: ExtractionResult) -> dict[str, int]:
        if not result.concepts and not result.relations:
            return {"concepts_added": 0, "edges_added": 0}

        with self._lock:
            graph = self._ensure_user_graph(user_id)
            concept_store = graph["concepts"]
            edge_store = graph["edges"]

            concepts_added = 0
            for concept in result.concepts:
                term = normalize_term(concept.term)
                if not term:
                    continue
                existing = concept_store.get(term)
                if not isinstance(existing, dict):
                    concept_store[term] = {
                        "kind": concept.kind,
                        "score": float(concept.score),
                        "frequency": int(concept.frequency),
                    }
                    concepts_added += 1
                    continue

                existing["frequency"] = int(existing.get("frequency", 0)) + int(concept.frequency)
                existing["score"] = max(float(existing.get("score", 0.0)), float(concept.score))
                if existing.get("kind") == "term" and concept.kind != "term":
                    existing["kind"] = concept.kind

            edges_added = 0
            for relation in result.relations:
                source = normalize_term(relation.source)
                target = normalize_term(relation.target)
                if not source or not target or source == target:
                    continue
                key = _edge_key(source, relation.relation, target)
                if key not in edge_store:
                    edges_added += 1
                edge_store[key] = int(edge_store.get(key, 0)) + int(relation.weight)

            self._save()

        if self._db_sync_enabled():
            try:
                self._sync_concepts_to_db(user_id=user_id, concepts=result.concepts)
                self._sync_relations_to_db(user_id=user_id, relations=result.relations)
            except Exception as exc:
                print(f"Learning graph DB sync error: {exc}")

        return {"concepts_added": concepts_added, "edges_added": edges_added}

    def get_concepts(self, user_id: str, limit: int = 100) -> list[dict[str, object]]:
        graph = self._data.get(user_id, {"concepts": {}, "edges": {}})
        concept_store = graph.get("concepts", {})
        items = []
        for term, meta in concept_store.items():
            if not isinstance(meta, dict):
                continue
            items.append(
                {
                    "term": term,
                    "kind": str(meta.get("kind", "term")),
                    "score": float(meta.get("score", 0.0)),
                    "frequency": int(meta.get("frequency", 0)),
                }
            )
        items.sort(key=lambda item: (item["frequency"], item["score"]), reverse=True)
        return items[:limit]

    def get_graph(
        self,
        user_id: str,
        max_nodes: int = 100,
        max_edges: int = 200,
    ) -> dict[str, list[dict[str, object]]]:
        concepts = self.get_concepts(user_id=user_id, limit=max_nodes)
        allowed = {str(item["term"]) for item in concepts}

        graph = self._data.get(user_id, {"concepts": {}, "edges": {}})
        edges: list[dict[str, object]] = []
        for raw_key, weight in graph.get("edges", {}).items():
            source, relation, target = _parse_edge_key(raw_key)
            if allowed and (source not in allowed or target not in allowed):
                continue
            edges.append(
                {
                    "source": source,
                    "relation": relation,
                    "target": target,
                    "weight": int(weight),
                }
            )

        edges.sort(key=lambda item: item["weight"], reverse=True)
        return {"nodes": concepts, "edges": edges[:max_edges]}

    def get_user_graph(
        self,
        user_id: str,
        max_nodes: int = 100,
        max_edges: int = 200,
    ) -> dict[str, list[dict[str, object]]]:
        return self.get_graph(
            user_id=user_id,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    def related_terms(self, user_id: str, term: str, limit: int = 20) -> list[dict[str, object]]:
        target = normalize_term(term)
        graph = self._data.get(user_id, {"concepts": {}, "edges": {}})
        relations = []
        for raw_key, weight in graph.get("edges", {}).items():
            source, relation, dest = _parse_edge_key(raw_key)
            if source == target:
                relations.append(
                    {"term": dest, "relation": relation, "weight": int(weight), "direction": "out"}
                )
            elif dest == target:
                relations.append(
                    {"term": source, "relation": relation, "weight": int(weight), "direction": "in"}
                )

        relations.sort(key=lambda item: item["weight"], reverse=True)
        return relations[:limit]

    def build_context(self, user_id: str, query: str, limit: int = 8) -> list[str]:
        related_map: dict[str, list[dict[str, object]]] = defaultdict(list)
        query_terms = [normalize_term(part) for part in query.split() if part.strip()]
        for term in query_terms:
            for rel in self.related_terms(user_id=user_id, term=term, limit=4):
                related_map[term].append(rel)

        if not related_map:
            concepts = self.get_concepts(user_id=user_id, limit=5)
            if not concepts:
                return []
            return [
                "[Graph concepts]\n"
                + ", ".join(f"{c['term']}({c['frequency']})" for c in concepts)
            ]

        lines: list[str] = []
        for term, rels in related_map.items():
            pair_text = "; ".join(
                f"{term} -[{rel['relation']}]-> {rel['term']} (w={rel['weight']})"
                for rel in rels[:limit]
            )
            lines.append(f"[Graph related]\n{pair_text}")
        return lines


learning_graph_store = LearningGraphStore(Path(settings.graph_path) / "learning_graph.json")
