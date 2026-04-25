from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.learning.clustering import concept_cluster_engine
from app.learning.graph import learning_graph_store
from app.learning.reflection import reflection_engine
from app.memory.long_term import LongTermMemoryStore, long_term_memory


TOKEN_PATTERN = re.compile(r"(?u)\b\w{3,}\b")
EMPHASIS_MARKERS = (
    "onemli",
    "important",
    "remember",
    "hatirla",
    "kaydet",
    "bunu hatirla",
    "bunu kaydet",
    "unutma",
    "must",
    "kritik",
)


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text or "")}


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class MemoryScoringEngine:
    def __init__(
        self,
        memory_store: LongTermMemoryStore = long_term_memory,
        graph_store=learning_graph_store,
        cluster_engine=concept_cluster_engine,
        reflection=reflection_engine,
    ):
        self.memory_store = memory_store
        self.graph_store = graph_store
        self.cluster_engine = cluster_engine
        self.reflection = reflection

    def _graph_strength(self, user_id: str) -> dict[str, float]:
        graph = self.graph_store.get_graph(user_id=user_id, max_nodes=240, max_edges=500)
        node_score: dict[str, float] = defaultdict(float)
        for edge in graph.get("edges", []):
            src = str(edge.get("source", ""))
            tgt = str(edge.get("target", ""))
            weight = float(edge.get("weight", 1))
            if src:
                node_score[src] += weight
            if tgt:
                node_score[tgt] += weight
        return node_score

    def _reflection_tokens(self, user_id: str) -> set[str]:
        summary = self.reflection.get_summary(user_id=user_id)
        text = " ".join(
            [
                str(summary.get("summary", "")),
                str(summary.get("user_preferences", "")),
                str(summary.get("stable_rules", "")),
                str(summary.get("project_focus", "")),
            ]
        )
        return _tokenize(text)

    def _cluster_terms(self, user_id: str) -> set[str]:
        clusters = self.cluster_engine.list_clusters(user_id=user_id, limit=30)
        terms: set[str] = set()
        for cluster in clusters:
            terms.update(str(term).lower() for term in cluster.get("terms", []))
        return terms

    def _score_item(
        self,
        item: dict[str, object],
        query_tokens: set[str],
        repetitions: Counter[str],
        correction_tokens: set[str],
        graph_strength: dict[str, float],
        reflection_tokens: set[str],
        cluster_terms: set[str],
    ) -> tuple[float, dict[str, float]]:
        text = str(item.get("text", ""))
        kind = str(item.get("kind", ""))
        tokens = _tokenize(text)

        signals: dict[str, float] = {}
        score = float(settings.memory_importance_default)

        repetition_count = max(0, repetitions[text.lower()] - 1)
        repeat_bonus = min(2.4, repetition_count * 0.35)
        signals["repetition"] = repeat_bonus
        score += repeat_bonus

        correction_overlap = len(tokens.intersection(correction_tokens))
        correction_bonus = min(1.2, correction_overlap * 0.2)
        if kind == "correction":
            correction_bonus += 0.5
        signals["correction"] = correction_bonus
        score += correction_bonus

        graph_bonus = 0.0
        if tokens:
            graph_bonus = min(1.5, sum(graph_strength.get(token, 0.0) for token in tokens) / 40.0)
        signals["graph"] = graph_bonus
        score += graph_bonus

        reflection_bonus = min(1.0, len(tokens.intersection(reflection_tokens)) * 0.18)
        signals["reflection"] = reflection_bonus
        score += reflection_bonus

        cluster_bonus = min(1.0, len(tokens.intersection(cluster_terms)) * 0.15)
        signals["cluster"] = cluster_bonus
        score += cluster_bonus

        emphasis_bonus = 0.0
        lower_text = text.lower()
        if any(marker in lower_text for marker in EMPHASIS_MARKERS):
            emphasis_bonus = 1.1
        signals["emphasis"] = emphasis_bonus
        score += emphasis_bonus

        query_bonus = min(1.5, len(tokens.intersection(query_tokens)) * 0.35)
        signals["query"] = query_bonus
        score += query_bonus

        recency_multiplier = 1.0
        created_at = str(item.get("created_at", ""))
        if created_at:
            try:
                age_days = max(
                    0.0,
                    (datetime.now(tz=timezone.utc) - _parse_datetime(created_at)).total_seconds() / 86400.0,
                )
                decay_days = max(1.0, float(settings.memory_decay_days))
                recency_multiplier = math.exp(-age_days / decay_days)
            except Exception:
                recency_multiplier = 1.0
        signals["recency_multiplier"] = recency_multiplier
        score *= 0.55 + (0.45 * recency_multiplier)

        return round(score, 4), {key: round(value, 4) for key, value in signals.items()}

    def top_memories(self, user_id: str, query: str = "", limit: int = 10) -> list[dict[str, object]]:
        items = self.memory_store.list_user(user_id=user_id, limit=1500)
        if not items:
            return []

        repetitions = Counter(str(item.get("text", "")).lower() for item in items if item.get("text"))
        correction_text = " ".join(
            str(item.get("text", ""))
            for item in items
            if str(item.get("kind", "")) == "correction"
        )
        correction_tokens = _tokenize(correction_text)
        graph_strength = self._graph_strength(user_id=user_id)
        reflection_tokens = self._reflection_tokens(user_id=user_id)
        cluster_terms = self._cluster_terms(user_id=user_id)
        query_tokens = _tokenize(query)

        scored: list[dict[str, object]] = []
        for item in items:
            score, signals = self._score_item(
                item=item,
                query_tokens=query_tokens,
                repetitions=repetitions,
                correction_tokens=correction_tokens,
                graph_strength=graph_strength,
                reflection_tokens=reflection_tokens,
                cluster_terms=cluster_terms,
            )
            scored.append(
                {
                    **item,
                    "importance_score": score,
                    "score_signals": signals,
                }
            )

        scored.sort(key=lambda entry: float(entry.get("importance_score", 0.0)), reverse=True)
        return scored[:limit]

    def build_chat_context(self, user_id: str, query: str, limit: int = 4) -> list[str]:
        memories = self.top_memories(user_id=user_id, query=query, limit=limit)
        output: list[str] = []
        for item in memories:
            output.append(
                f"[Top memory score={item['importance_score']} kind={item.get('kind','')}]\n"
                f"{item.get('text','')}"
            )
        return output


memory_scoring_engine = MemoryScoringEngine()

