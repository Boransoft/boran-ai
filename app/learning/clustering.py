from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx

from app.config import settings
from app.db.sync import sync_memory_item
from app.learning.graph import learning_graph_store
from app.memory.long_term import LongTermMemoryStore, long_term_memory


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


class ConceptClusterEngine:
    def __init__(
        self,
        graph_store=learning_graph_store,
        memory_store: LongTermMemoryStore = long_term_memory,
    ):
        self.graph_store = graph_store
        self.memory_store = memory_store

    def _label_for_terms(self, terms: list[str]) -> str:
        if not terms:
            return "genel kavramlar"
        if len(terms) == 1:
            return terms[0]
        return f"{terms[0]} ve {terms[1]}"

    def build_clusters(
        self,
        user_id: str,
        max_nodes: int = 180,
        max_edges: int = 360,
    ) -> list[dict[str, object]]:
        graph_payload = self.graph_store.get_graph(
            user_id=user_id,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
        node_frequency: dict[str, int] = {
            str(node.get("term")): int(node.get("frequency", 0))
            for node in graph_payload.get("nodes", [])
            if node.get("term")
        }

        graph = nx.Graph()
        for term, frequency in node_frequency.items():
            graph.add_node(term, frequency=frequency)

        for edge in graph_payload.get("edges", []):
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            if not source or not target or source == target:
                continue
            weight = int(edge.get("weight", 1))
            if graph.has_edge(source, target):
                graph[source][target]["weight"] += weight
            else:
                graph.add_edge(source, target, weight=weight, relation=str(edge.get("relation", "")))

        min_size = max(2, int(settings.cluster_min_size))
        clusters: list[dict[str, object]] = []

        for component_index, component in enumerate(nx.connected_components(graph)):
            terms = sorted(
                component,
                key=lambda term: graph.nodes[term].get("frequency", 0),
                reverse=True,
            )
            if len(terms) < min_size:
                continue

            subgraph = graph.subgraph(component)
            edge_weight_sum = sum(int(data.get("weight", 1)) for _, _, data in subgraph.edges(data=True))
            score = round(edge_weight_sum / max(1, len(terms)), 4)
            cluster_id = f"{user_id}:cluster:{component_index}:{terms[0]}"
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "label": self._label_for_terms(terms[:4]),
                    "size": len(terms),
                    "score": score,
                    "terms": terms[:20],
                    "generated_at": _now_iso(),
                }
            )

        clusters.sort(key=lambda item: (float(item["score"]), int(item["size"])), reverse=True)
        return clusters

    def persist_clusters(self, user_id: str, clusters: list[dict[str, object]]) -> int:
        if not clusters:
            return 0

        existing = self.list_clusters(user_id=user_id, limit=200, fallback=False)
        existing_keys = {
            (str(item.get("label")), ",".join(item.get("terms", [])))
            for item in existing
        }

        inserted = 0
        for rank, cluster in enumerate(clusters, start=1):
            key = (str(cluster.get("label", "")), ",".join(cluster.get("terms", [])))
            if key in existing_keys:
                continue

            metadata = {
                "cluster_id": str(cluster.get("cluster_id", "")),
                "size": str(cluster.get("size", 0)),
                "score": str(cluster.get("score", 0.0)),
                "terms": ",".join(cluster.get("terms", [])),
                "rank": str(rank),
                "generated_at": str(cluster.get("generated_at", _now_iso())),
            }
            text = str(cluster.get("label", ""))
            self.memory_store.add(
                user_id=user_id,
                text=text,
                kind="concept_cluster",
                source="cluster_engine",
                metadata=metadata,
            )
            inserted += 1

            if settings.database_url:
                try:
                    sync_memory_item(
                        user_external_id=user_id,
                        kind="concept_cluster",
                        text=text,
                        source="cluster_engine",
                        metadata_json=metadata,
                    )
                except Exception as exc:
                    print(f"Cluster DB sync error: {exc}")
        return inserted

    def refresh_user_clusters(self, user_id: str) -> dict[str, object]:
        clusters = self.build_clusters(user_id=user_id)
        inserted = self.persist_clusters(user_id=user_id, clusters=clusters)
        return {
            "clusters": clusters,
            "inserted": inserted,
        }

    def list_clusters(
        self,
        user_id: str,
        limit: int = 20,
        fallback: bool = True,
    ) -> list[dict[str, object]]:
        records = self.memory_store.list_user(user_id=user_id, limit=max(200, limit * 5))
        output: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()

        for item in records:
            if str(item.get("kind")) != "concept_cluster":
                continue
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            label = str(item.get("text", ""))
            terms = [term.strip() for term in str(metadata.get("terms", "")).split(",") if term.strip()]
            key = (label, ",".join(terms))
            if key in seen:
                continue
            seen.add(key)

            output.append(
                {
                    "cluster_id": str(metadata.get("cluster_id", "")),
                    "label": label,
                    "size": int(metadata.get("size", len(terms) or 1)),
                    "score": _safe_float(metadata.get("score", 0.0)),
                    "terms": terms,
                    "generated_at": str(metadata.get("generated_at", item.get("created_at", ""))),
                }
            )
            if len(output) >= limit:
                break

        if output:
            return output
        if fallback:
            return self.build_clusters(user_id=user_id)[:limit]
        return []

    def build_chat_context(self, user_id: str, query: str, limit: int = 3) -> list[str]:
        query_tokens = {token.strip().lower() for token in query.split() if token.strip()}
        clusters = self.list_clusters(user_id=user_id, limit=max(10, limit * 4))

        ranked: list[tuple[float, dict[str, object]]] = []
        for cluster in clusters:
            terms = [str(term).lower() for term in cluster.get("terms", [])]
            overlap = len(query_tokens.intersection(set(terms)))
            score = float(cluster.get("score", 0.0)) + overlap * 0.8
            ranked.append((score, cluster))

        ranked.sort(key=lambda item: item[0], reverse=True)

        output: list[str] = []
        for _, cluster in ranked[:limit]:
            terms_text = ", ".join(cluster.get("terms", [])[:8])
            output.append(
                f"[Concept cluster label={cluster['label']} score={cluster['score']}]\n{terms_text}"
            )
        return output


concept_cluster_engine = ConceptClusterEngine()
