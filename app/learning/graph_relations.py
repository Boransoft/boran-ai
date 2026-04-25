from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from itertools import combinations

from app.config import settings
from app.learning.concepts import Concept, ExtractionResult, Relation, normalize_term
from app.rag.ingest import split_text


SUPPORTED_RELATIONS = {
    "related_to",
    "part_of",
    "mentions",
    "uses",
    "requires",
    "belongs_to",
    "defined_as",
    "semantically_related",
}

SYMMETRIC_RELATIONS = {"related_to", "semantically_related"}
SENTENCE_SPLIT = re.compile(r"[.!?\n]+")

RELATION_HINTS: dict[str, tuple[str, ...]] = {
    "defined_as": ("defined as", "is called", "olarak tanimlan", "olarak tanim"),
    "part_of": ("part of", "parcasi", "parcasidir"),
    "belongs_to": ("belongs to", "aittir", "ait"),
    "uses": (" uses ", " use ", "kullanir", "kullanilir", "kullaniyor"),
    "requires": (" requires ", " need ", " needs ", "gerektir", "ihtiyac"),
    "mentions": (" mentions ", "mentions", "bahseder", "anilir"),
}


def normalize_relation(value: str) -> str:
    relation = normalize_term(value).replace(" ", "_")
    if relation not in SUPPORTED_RELATIONS:
        return "related_to"
    return relation


def canonicalize_relation(source: str, relation: str, target: str) -> tuple[str, str, str]:
    src = normalize_term(source)
    tgt = normalize_term(target)
    rel = normalize_relation(relation)
    if rel in SYMMETRIC_RELATIONS and src > tgt:
        return tgt, rel, src
    return src, rel, tgt


def _find_terms_in_text(text: str, terms: set[str]) -> list[str]:
    found: list[str] = []
    sentence = f" {normalize_term(text)} "
    for term in sorted(terms, key=len, reverse=True):
        if not term:
            continue
        if f" {term} " in sentence and term not in found:
            found.append(term)
    return found


def _keyword_relation(sentence: str) -> str:
    sentence_l = f" {normalize_term(sentence)} "
    for relation, markers in RELATION_HINTS.items():
        if any(marker in sentence_l for marker in markers):
            return relation
    return "mentions"


def _co_occurrence_relations(
    text: str,
    terms: list[str],
    window: int,
) -> list[Relation]:
    if len(terms) < 2 or not text.strip():
        return []

    unique_terms = sorted({normalize_term(term) for term in terms if normalize_term(term)})
    pair_counter: Counter[tuple[str, str]] = Counter()
    chunks = split_text(text, chunk_size=520, overlap=80)

    for chunk in chunks:
        hits = _find_terms_in_text(chunk, set(unique_terms))
        if len(hits) < 2:
            continue
        for i, left in enumerate(hits):
            for right in hits[i + 1 : i + 1 + max(1, window)]:
                src, _, tgt = canonicalize_relation(left, "related_to", right)
                if src != tgt:
                    pair_counter[(src, tgt)] += 1

    return [
        Relation(source=src, relation="related_to", target=tgt, weight=int(weight))
        for (src, tgt), weight in pair_counter.items()
    ]


def _sentence_relations(text: str, terms: list[str]) -> list[Relation]:
    if len(terms) < 2 or not text.strip():
        return []

    known = set(terms)
    counter: Counter[tuple[str, str, str]] = Counter()
    for sentence in SENTENCE_SPLIT.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        hits = _find_terms_in_text(sentence, known)
        if len(hits) < 2:
            continue
        relation = _keyword_relation(sentence)

        for left, right in combinations(hits[:6], 2):
            src, rel, tgt = canonicalize_relation(left, relation, right)
            if src and tgt and src != tgt:
                counter[(src, rel, tgt)] += 1

    return [
        Relation(source=src, relation=rel, target=tgt, weight=int(weight))
        for (src, rel, tgt), weight in counter.items()
    ]


def merge_relations(relations: list[Relation]) -> list[Relation]:
    merged: dict[tuple[str, str, str], Relation] = {}
    for relation in relations:
        src, rel, tgt = canonicalize_relation(
            relation.source,
            relation.relation,
            relation.target,
        )
        if not src or not tgt or src == tgt:
            continue
        key = (src, rel, tgt)
        if key in merged:
            merged[key].weight += int(relation.weight)
        else:
            merged[key] = replace(
                relation,
                source=src,
                relation=rel,
                target=tgt,
                weight=int(relation.weight),
            )
    return list(merged.values())


class GraphRelationEngine:
    def enrich(self, text: str, extraction: ExtractionResult) -> ExtractionResult:
        concept_terms = [normalize_term(concept.term) for concept in extraction.concepts]
        concept_terms = [term for term in concept_terms if term]
        window = max(1, int(settings.graph_co_occurrence_window))

        relations = list(extraction.relations)
        relations.extend(_co_occurrence_relations(text=text, terms=concept_terms, window=window))
        relations.extend(_sentence_relations(text=text, terms=concept_terms))

        return ExtractionResult(
            concepts=extraction.concepts,
            relations=merge_relations(relations),
        )


graph_relation_engine = GraphRelationEngine()
