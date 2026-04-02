from dataclasses import dataclass, field


@dataclass
class Concept:
    term: str
    kind: str
    score: float = 1.0
    frequency: int = 1
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    relation: str
    target: str
    weight: int = 1


@dataclass
class ExtractionResult:
    concepts: list[Concept]
    relations: list[Relation]


def normalize_term(term: str) -> str:
    return term.strip().lower()
