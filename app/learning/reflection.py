from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.config import settings
from app.db.sync import sync_memory_item
from app.learning.graph import learning_graph_store
from app.memory.long_term import LongTermMemoryStore, long_term_memory


REFLECTION_KINDS = (
    "recurring_topics",
    "user_preferences",
    "project_focus",
    "stable_rules",
    "concept_clusters",
    "recent_learning_summary",
)

CONVERSATION_KINDS = {"semantic_conversation", "user_message", "assistant_reply"}
DOCUMENT_KINDS = {"semantic_document"}
CORRECTION_KINDS = {"correction"}

PREFERENCE_MARKERS = (
    "tercih",
    "istiyor",
    "ister",
    "seviyor",
    "onemli",
    "gerekli",
    "kullan",
    "want",
    "prefer",
    "likes",
    "important",
)

RULE_MARKERS = (
    "her zaman",
    "asla",
    "mutlaka",
    "kural",
    "gerekir",
    "olmasin",
    "always",
    "never",
    "must",
    "should",
)


def _compact(text: str, max_chars: int = 260) -> str:
    value = " ".join(text.strip().split())
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def _split_sentences(text: str) -> list[str]:
    raw_parts = re.split(r"[\n\.!?]+", text)
    return [part.strip() for part in raw_parts if part and part.strip()]


def _parse_correction_item(text: str) -> tuple[str, str]:
    original = ""
    corrected = ""
    for line in text.splitlines():
        clean = line.strip()
        if clean.lower().startswith("original answer:"):
            original = clean.split(":", 1)[1].strip() if ":" in clean else ""
        if clean.lower().startswith("corrected answer:"):
            corrected = clean.split(":", 1)[1].strip() if ":" in clean else ""
    return original, corrected


@dataclass
class ReflectionSnapshot:
    conversations: list[dict[str, object]]
    documents: list[dict[str, object]]
    corrections: list[dict[str, object]]
    graph_nodes: list[dict[str, object]]
    graph_edges: list[dict[str, object]]


class ReflectionEngine:
    def __init__(
        self,
        memory_store: LongTermMemoryStore = long_term_memory,
        graph_store=learning_graph_store,
    ):
        self.memory_store = memory_store
        self.graph_store = graph_store

    def _collect_snapshot(self, user_id: str) -> ReflectionSnapshot:
        items = self.memory_store.list_user(user_id=user_id, limit=900)
        conversations = [item for item in items if str(item.get("kind")) in CONVERSATION_KINDS][:80]
        documents = [item for item in items if str(item.get("kind")) in DOCUMENT_KINDS][:60]
        corrections = [item for item in items if str(item.get("kind")) in CORRECTION_KINDS][:60]

        if hasattr(self.graph_store, "get_graph"):
            graph = self.graph_store.get_graph(user_id=user_id, max_nodes=120, max_edges=200)
        else:
            graph = self.graph_store.get_user_graph(user_id=user_id, max_nodes=120, max_edges=200)
        strong_edges = [edge for edge in graph["edges"] if int(edge.get("weight", 0)) >= 2]

        return ReflectionSnapshot(
            conversations=conversations,
            documents=documents,
            corrections=corrections,
            graph_nodes=graph["nodes"],
            graph_edges=strong_edges[:40] if strong_edges else graph["edges"][:40],
        )

    def _build_recurring_topics(self, snapshot: ReflectionSnapshot) -> str:
        if not snapshot.graph_nodes:
            return ""

        top = snapshot.graph_nodes[:8]
        joined = ", ".join(f"{node['term']}({node['frequency']})" for node in top)
        return f"Tekrar eden ana konular: {joined}."

    def _build_user_preferences(self, snapshot: ReflectionSnapshot) -> str:
        preference_sentences: list[str] = []
        source_items = snapshot.conversations + snapshot.corrections

        for item in source_items:
            for sentence in _split_sentences(str(item.get("text", ""))):
                lower = sentence.lower()
                if any(marker in lower for marker in PREFERENCE_MARKERS):
                    preference_sentences.append(_compact(sentence, max_chars=180))

        unique: list[str] = []
        seen = set()
        for sentence in preference_sentences:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(sentence)
            if len(unique) >= 5:
                break

        if not unique:
            return ""

        return "Kullanici tercihleri: " + " | ".join(unique)

    def _build_project_focus(self, snapshot: ReflectionSnapshot) -> str:
        if not snapshot.documents:
            return ""

        categories = Counter()
        recency_samples: list[str] = []
        for item in snapshot.documents[:12]:
            metadata = item.get("metadata", {})
            if isinstance(metadata, dict):
                categories[str(metadata.get("category", "general"))] += 1
            text = str(item.get("text", ""))
            if text:
                recency_samples.append(_compact(text, max_chars=120))

        cat_text = ", ".join(f"{name}({count})" for name, count in categories.most_common(4))
        sample_text = " | ".join(recency_samples[:3])
        return f"Proje odagi: kategoriler={cat_text}. Son dokuman vurgulari: {sample_text}"

    def _build_stable_rules(self, snapshot: ReflectionSnapshot) -> str:
        rules: list[str] = []

        for item in snapshot.corrections:
            _, corrected = _parse_correction_item(str(item.get("text", "")))
            if corrected:
                rules.append(_compact(corrected, max_chars=170))

        for item in snapshot.conversations[:20]:
            for sentence in _split_sentences(str(item.get("text", ""))):
                lower = sentence.lower()
                if any(marker in lower for marker in RULE_MARKERS):
                    rules.append(_compact(sentence, max_chars=170))

        unique: list[str] = []
        seen = set()
        for rule in rules:
            key = rule.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(rule)
            if len(unique) >= 6:
                break

        if not unique:
            return ""

        return "Kalici kurallar: " + " | ".join(unique)

    def _build_concept_clusters(self, snapshot: ReflectionSnapshot) -> str:
        if not snapshot.graph_edges:
            return ""

        chunks: list[str] = []
        for edge in snapshot.graph_edges[:10]:
            chunks.append(
                f"{edge['source']} -[{edge['relation']}, w={edge['weight']}]-> {edge['target']}"
            )
        return "Kavram kumeleri: " + " | ".join(chunks)

    def _build_recent_learning_summary(self, snapshot: ReflectionSnapshot, generated: dict[str, str]) -> str:
        count_conv = len(snapshot.conversations)
        count_docs = len(snapshot.documents)
        count_corr = len(snapshot.corrections)
        count_edges = len(snapshot.graph_edges)

        highlights: list[str] = []
        if generated.get("recurring_topics"):
            highlights.append(generated["recurring_topics"])
        if generated.get("project_focus"):
            highlights.append(generated["project_focus"])

        head = (
            "Son ogrenme ozeti: "
            f"konusma={count_conv}, dokuman={count_docs}, correction={count_corr}, guclu_iliski={count_edges}."
        )
        if not highlights:
            return head

        return head + " " + " ".join(_compact(text, max_chars=220) for text in highlights[:2])

    def _latest_reflection_by_kind(self, user_id: str) -> dict[str, str]:
        latest: dict[str, str] = {}
        for item in self.list_reflections(user_id=user_id, limit=180):
            kind = str(item.get("kind", ""))
            if kind not in REFLECTION_KINDS:
                continue
            if kind in latest:
                continue
            latest[kind] = str(item.get("text", ""))
        return latest

    def _persist_reflections(self, user_id: str, generated: dict[str, str], snapshot: ReflectionSnapshot) -> int:
        latest_by_kind = self._latest_reflection_by_kind(user_id=user_id)
        stored = 0

        for kind in REFLECTION_KINDS:
            text = generated.get(kind, "").strip()
            if not text:
                continue
            if latest_by_kind.get(kind, "") == text:
                continue

            metadata = {
                "conversation_count": str(len(snapshot.conversations)),
                "document_count": str(len(snapshot.documents)),
                "correction_count": str(len(snapshot.corrections)),
                "edge_count": str(len(snapshot.graph_edges)),
            }
            self.memory_store.add(
                user_id=user_id,
                text=text,
                kind=kind,
                source="reflection_engine",
                metadata=metadata,
            )
            stored += 1

            if settings.database_url:
                try:
                    sync_memory_item(
                        user_external_id=user_id,
                        kind=kind,
                        text=text,
                        source="reflection_engine",
                        metadata_json=metadata,
                    )
                except Exception as exc:
                    print(f"Reflection DB sync error: {exc}")

        return stored

    def reflect_user(self, user_id: str, persist: bool = True) -> dict[str, object]:
        snapshot = self._collect_snapshot(user_id=user_id)

        generated = {
            "recurring_topics": self._build_recurring_topics(snapshot),
            "user_preferences": self._build_user_preferences(snapshot),
            "project_focus": self._build_project_focus(snapshot),
            "stable_rules": self._build_stable_rules(snapshot),
            "concept_clusters": self._build_concept_clusters(snapshot),
        }
        generated["recent_learning_summary"] = self._build_recent_learning_summary(snapshot, generated)

        stored_count = 0
        if persist:
            stored_count = self._persist_reflections(
                user_id=user_id,
                generated=generated,
                snapshot=snapshot,
            )

        return {
            "status": "ok",
            "user_id": user_id,
            "generated": {kind: text for kind, text in generated.items() if text.strip()},
            "stored_count": stored_count,
            "source_counts": {
                "conversations": len(snapshot.conversations),
                "documents": len(snapshot.documents),
                "corrections": len(snapshot.corrections),
                "strong_edges": len(snapshot.graph_edges),
            },
        }

    def list_reflections(self, user_id: str, limit: int = 40) -> list[dict[str, object]]:
        items = self.memory_store.list_user(user_id=user_id, limit=max(200, limit * 4))
        reflections = [item for item in items if str(item.get("kind")) in REFLECTION_KINDS]
        reflections.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return reflections[:limit]

    def get_summary(self, user_id: str) -> dict[str, object]:
        reflections = self.list_reflections(user_id=user_id, limit=200)
        latest_by_kind: dict[str, dict[str, object]] = {}
        for item in reflections:
            kind = str(item.get("kind", ""))
            if kind in latest_by_kind:
                continue
            latest_by_kind[kind] = item

        latest_summary = latest_by_kind.get("recent_learning_summary")
        return {
            "user_id": user_id,
            "summary": str(latest_summary.get("text", "")) if latest_summary else "",
            "generated_at": str(latest_summary.get("created_at", "")) if latest_summary else "",
            "user_preferences": str(latest_by_kind.get("user_preferences", {}).get("text", "")),
            "stable_rules": str(latest_by_kind.get("stable_rules", {}).get("text", "")),
            "project_focus": str(latest_by_kind.get("project_focus", {}).get("text", "")),
            "recurring_topics": str(latest_by_kind.get("recurring_topics", {}).get("text", "")),
            "concept_clusters": str(latest_by_kind.get("concept_clusters", {}).get("text", "")),
        }

    def build_chat_context(self, user_id: str) -> list[str]:
        summary = self.get_summary(user_id=user_id)
        parts: list[str] = []
        if summary.get("user_preferences"):
            parts.append(f"[Reflection user_preferences]\n{summary['user_preferences']}")
        if summary.get("stable_rules"):
            parts.append(f"[Reflection stable_rules]\n{summary['stable_rules']}")
        if summary.get("summary"):
            parts.append(f"[Reflection summary]\n{summary['summary']}")
        return parts


reflection_engine = ReflectionEngine()
