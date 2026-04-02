import re

from app.knowledge.text_processing import extract_concepts_with_positions


SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?\n]+")


RELATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "uses": (" uses ", " use ", " kullan", "kullanir", "kullanıyor", "kullanir"),
    "requires": (" requires ", " need ", " needs ", " gerektir", " ihtiyac"),
    "learns_from": (" learns from ", " ogrenir ", "öğrenir", "ogren", "ögren"),
    "improves": (" improves ", " improve ", " gelistir", "iyilestir"),
    "part_of": (" part of ", " parcasi ", " parcasidir "),
    "causes": (" causes ", " cause ", " neden olur "),
}


def _find_relation(sentence_lower: str) -> tuple[str, int] | None:
    for relation, keywords in RELATION_KEYWORDS.items():
        for keyword in keywords:
            idx = sentence_lower.find(keyword)
            if idx >= 0:
                return relation, idx
    return None


def _nearest_before(concepts: list[tuple[str, int]], index: int) -> str | None:
    candidates = [item for item in concepts if item[1] < index]
    if not candidates:
        return None
    return candidates[-1][0]


def _nearest_after(concepts: list[tuple[str, int]], index: int) -> str | None:
    candidates = [item for item in concepts if item[1] > index]
    if not candidates:
        return None
    return candidates[0][0]


def extract_relations(text: str) -> list[tuple[str, str, str]]:
    relations: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for raw_sentence in SENTENCE_SPLIT_PATTERN.split(text):
        sentence = raw_sentence.strip()
        if not sentence:
            continue

        sentence_lower = f" {sentence.lower()} "
        concepts = extract_concepts_with_positions(sentence)
        if len(concepts) < 2:
            continue

        relation_hit = _find_relation(sentence_lower)
        if not relation_hit:
            continue

        relation, keyword_index = relation_hit
        source = _nearest_before(concepts, keyword_index)
        target = _nearest_after(concepts, keyword_index)

        if not source or not target or source == target:
            continue

        triple = (source, relation, target)
        if triple in seen:
            continue
        seen.add(triple)
        relations.append(triple)

    return relations
