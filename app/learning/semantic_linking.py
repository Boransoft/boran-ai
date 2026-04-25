from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Callable

from app.config import settings
from app.learning.concepts import Relation, normalize_term
from app.learning.graph import learning_graph_store
from app.learning.graph_relations import canonicalize_relation
from app.rag.embeddings import encode_texts


TOKEN_PATTERN = re.compile(r"(?u)\b\w{3,}\b")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _query_terms(text: str, max_terms: int = 5) -> list[str]:
    terms = [normalize_term(match.group(0)) for match in TOKEN_PATTERN.finditer(text or "")]
    ordered: list[str] = []
    for term in terms:
        if term not in ordered:
            ordered.append(term)
        if len(ordered) >= max_terms:
            break
    return ordered


class SemanticLinker:
    def __init__(
        self,
        graph_store=learning_graph_store,
        embedder: Callable[[list[str]], list[list[float]]] = encode_texts,
    ):
        self.graph_store = graph_store
        self.embedder = embedder

    def _threshold(self) -> float:
        value = float(settings.semantic_link_threshold)
        return min(0.99, max(0.0, value))

    def _existing_terms(self, user_id: str, limit: int = 150) -> list[str]:
        concepts = self.graph_store.get_concepts(user_id=user_id, limit=limit)
        return [normalize_term(str(item.get("term", ""))) for item in concepts if item.get("term")]

    def build_semantic_relations(
        self,
        user_id: str,
        terms: list[str],
        max_new_terms: int = 60,
    ) -> list[Relation]:
        threshold = self._threshold()
        new_terms: list[str] = []
        for term in terms:
            normalized = normalize_term(term)
            if normalized and normalized not in new_terms:
                new_terms.append(normalized)
            if len(new_terms) >= max_new_terms:
                break

        if len(new_terms) < 2:
            return []

        existing_terms = self._existing_terms(user_id=user_id, limit=180)
        candidate_terms = list(new_terms)
        for term in existing_terms:
            if term not in candidate_terms:
                candidate_terms.append(term)
            if len(candidate_terms) >= 260:
                break

        vectors = self.embedder(candidate_terms)
        if len(vectors) != len(candidate_terms):
            return []

        top_hits_by_term: dict[str, list[tuple[str, float]]] = defaultdict(list)
        new_set = set(new_terms)

        for i, left in enumerate(candidate_terms):
            if left not in new_set:
                continue
            left_vec = vectors[i]
            for j in range(i + 1, len(candidate_terms)):
                right = candidate_terms[j]
                if left == right:
                    continue
                similarity = _cosine_similarity(left_vec, vectors[j])
                if similarity < threshold:
                    continue
                top_hits_by_term[left].append((right, similarity))
                top_hits_by_term[right].append((left, similarity))

        relations: list[Relation] = []
        for term, hits in top_hits_by_term.items():
            for neighbor, score in sorted(hits, key=lambda x: x[1], reverse=True)[:4]:
                src, _, tgt = canonicalize_relation(term, "semantically_related", neighbor)
                if src == tgt:
                    continue
                weight = max(1, int(round(score * 4)))
                relations.append(
                    Relation(
                        source=src,
                        relation="semantically_related",
                        target=tgt,
                        weight=weight,
                    )
                )

        dedup: dict[tuple[str, str, str], Relation] = {}
        for relation in relations:
            key = (relation.source, relation.relation, relation.target)
            prev = dedup.get(key)
            if prev:
                prev.weight = max(prev.weight, relation.weight)
            else:
                dedup[key] = relation
        return list(dedup.values())

    def lookup_similar_terms(self, user_id: str, term: str, limit: int = 12) -> list[dict[str, object]]:
        query = normalize_term(term)
        if not query:
            return []

        concepts = self._existing_terms(user_id=user_id, limit=240)
        candidates = [concept for concept in concepts if concept != query]
        if not candidates:
            return []

        texts = [query] + candidates
        vectors = self.embedder(texts)
        if len(vectors) != len(texts):
            return []

        query_vec = vectors[0]
        threshold = self._threshold()
        matches: list[dict[str, object]] = []
        for index, candidate in enumerate(candidates, start=1):
            score = _cosine_similarity(query_vec, vectors[index])
            if score < threshold:
                continue
            matches.append(
                {
                    "term": candidate,
                    "score": round(float(score), 4),
                }
            )

        matches.sort(key=lambda item: float(item["score"]), reverse=True)
        return matches[:limit]

    def build_query_context(self, user_id: str, query: str, limit: int = 8) -> list[str]:
        parts: list[str] = []
        for term in _query_terms(query, max_terms=4):
            related = self.lookup_similar_terms(user_id=user_id, term=term, limit=4)
            if not related:
                continue
            relations = ", ".join(f"{item['term']}({item['score']})" for item in related)
            parts.append(f"[Semantic related term={term}]\n{relations}")
            if len(parts) >= limit:
                break
        return parts


semantic_linker = SemanticLinker()

