import re
from collections import Counter

from app.knowledge.relation_extractor import extract_relations
from app.knowledge.text_processing import extract_concepts
from app.learning.concepts import Concept, ExtractionResult, Relation, normalize_term


ENTITY_PATTERN = re.compile(r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\b")


class ConceptExtractor:
    """Baseline concept extractor designed for iterative upgrades."""

    def extract(self, text: str, top_k: int = 30) -> ExtractionResult:
        raw_text = text or ""
        tokens = [normalize_term(token) for token in extract_concepts(raw_text)]
        token_counter = Counter(tokens)

        concepts: list[Concept] = []
        for term, frequency in token_counter.most_common(top_k):
            score = min(1.0, 0.25 + (frequency / max(1, token_counter.most_common(1)[0][1])))
            concepts.append(
                Concept(
                    term=term,
                    kind="term",
                    score=round(score, 4),
                    frequency=int(frequency),
                    metadata={},
                )
            )

        entities = {normalize_term(match.group(0)) for match in ENTITY_PATTERN.finditer(raw_text)}
        for entity in sorted(entities):
            if not entity:
                continue
            if any(c.term == entity for c in concepts):
                continue
            concepts.append(
                Concept(
                    term=entity,
                    kind="entity",
                    score=0.9,
                    frequency=1,
                    metadata={},
                )
            )

        relation_hits = extract_relations(raw_text)
        relation_counter = Counter((normalize_term(s), r, normalize_term(t)) for s, r, t in relation_hits)
        relations: list[Relation] = [
            Relation(source=s, relation=r, target=t, weight=int(w))
            for (s, r, t), w in relation_counter.items()
            if s and t and s != t
        ]

        return ExtractionResult(concepts=concepts, relations=relations)


concept_extractor = ConceptExtractor()
