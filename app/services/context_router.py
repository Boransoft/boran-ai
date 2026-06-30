from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class RouteResult:
    area: str
    topic: str = ""
    intent: str = ""
    concepts: list[str] = field(default_factory=list)
    obsidian_keys: list[str] = field(default_factory=list)
    source_pool: str = ""
    confidence: float = 0.5


HAVAS_KEYWORDS = {
    "havas",
    "tılsım",
    "tilsim",
    "vefk",
    "ebced",
    "esma",
    "esmalar",
    "muska",
    "terkip",
    "dua",
    "zikir",
    "ibn arabi",
    "fususu",
    "fusûs",
    "fusus",
    "insan-ı kamil",
    "insan-i kamil",
}

IS_KEYWORDS = {
    "iş",
    "akıllı durak",
    "akilli durak",
    "otobüs",
    "otobus",
    "şartname",
    "sartname",
    "sözleşme",
    "sozlesme",
    "muayene",
    "kabul",
    "ihale",
    "led panel",
    "bilgisayar alımı",
    "bilgisayar alimi",
    "mal alımı",
    "mal alimi",
    "hizmet alımı",
    "hizmet alimi",
    "tutanak",
    "komisyon",
}

BORANAI_KEYWORDS = {
    "boran.ai",
    "boran ai",
    "backend",
    "mobil",
    "obsidian",
    "notebooklm",
    "chatgpt",
    "vektör",
    "vektor",
    "hafıza",
    "hafiza",
    "rag",
    "llm",
    "pdf öğrenme",
    "pdf ogrenme",
}

BORSA_KEYWORDS = {
    "borsa",
    "hisse",
    "portföy",
    "portfoy",
    "halka arz",
    "thyao",
    "astor",
    "ismen",
    "ansgr",
    "doas",
    "frmpl",
}


def _contains_any(text: str, keywords: set[str]) -> int:
    count = 0
    for keyword in keywords:
        if " " in keyword or "." in keyword:
            if keyword in text:
                count += 1
            continue
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, flags=re.IGNORECASE):
            count += 1
    return count


def _route(
    area: str,
    topic: str,
    intent: str,
    concepts: list[str],
    source_pool: str,
    score: int,
) -> RouteResult:
    unique_concepts = list(dict.fromkeys(concepts))
    return RouteResult(
        area=area,
        topic=topic,
        intent=intent,
        concepts=unique_concepts,
        obsidian_keys=unique_concepts,
        source_pool=source_pool,
        confidence=min(0.95, 0.55 + score * 0.08),
    )


def analyze_question(message: str) -> RouteResult:
    text = (message or "").lower()

    scores = {
        "Havas": _contains_any(text, HAVAS_KEYWORDS),
        "Is": _contains_any(text, IS_KEYWORDS),
        "Boran.ai": _contains_any(text, BORANAI_KEYWORDS),
        "Portfoy": _contains_any(text, BORSA_KEYWORDS),
    }

    area = max(scores, key=scores.get)
    best_score = scores[area]

    if best_score <= 0:
        return RouteResult(
            area="Genel",
            intent="genel_soru",
            obsidian_keys=["AnaSayfa"],
            confidence=0.35,
        )

    if area == "Havas":
        concepts = ["Havas", "Havas Kavramlari"]
        if any(k in text for k in ["tılsım", "tilsim", "muska", "terkip"]):
            concepts.append("Terkipler")
        if "vefk" in text:
            concepts.append("Vefkler")
        if any(k in text for k in ["esma", "esmalar", "zikir"]):
            concepts.append("Esmalar")
        if any(k in text for k in ["ebced", "harf", "sayı", "sayi"]):
            concepts.extend(["Ebced", "Harfler", "Sayilar"])
        return _route(
            area="Havas",
            topic="Havas",
            intent="havas_kaynak_arama",
            concepts=concepts,
            source_pool="BORAN.AI - Havas Ilmi",
            score=best_score,
        )

    if area == "Is":
        concepts = ["Is"]
        topic = "Is"
        if any(k in text for k in ["akıllı durak", "akilli durak", "led panel"]):
            concepts.append("Akilli Durak")
            topic = "Akilli Durak"
        if any(k in text for k in ["otobüs", "otobus"]):
            concepts.append("Otobus Alimi")
            topic = "Otobus Alimi"
        if any(k in text for k in ["muayene", "kabul", "komisyon"]):
            concepts.append("Muayene Kabul")
        if any(k in text for k in ["şartname", "sartname"]):
            concepts.append("Sartnameler")
        if any(k in text for k in ["sözleşme", "sozlesme"]):
            concepts.append("Sozlesmeler")
        return _route(
            area="Is",
            topic=topic,
            intent="is_soru",
            concepts=concepts,
            source_pool=f"BORAN.AI - {topic}",
            score=best_score,
        )

    if area == "Boran.ai":
        concepts = ["Boran.ai", "BoranAI Kavramlari"]
        if "mobil" in text:
            concepts.append("Mobil Asistan")
        if "notebooklm" in text:
            concepts.append("NotebookLM")
        if "obsidian" in text:
            concepts.append("Obsidian")
        if "vektör" in text or "vektor" in text:
            concepts.append("Vektor Hafiza")
        if "hafıza" in text or "hafiza" in text:
            concepts.append("Hafiza Sistemi")
        if "pdf" in text:
            concepts.extend(["PDF Ogrenme", "PDF Ogrenme Sistemi"])
        return _route(
            area="Boran.ai",
            topic="Boran.ai",
            intent="mimari_soru",
            concepts=concepts,
            source_pool="BORAN.AI - Sistem",
            score=best_score,
        )

    if area == "Portfoy":
        return _route(
            area="Portfoy",
            topic="Portfoy",
            intent="borsa_soru",
            concepts=["Portfoy"],
            source_pool="BORAN.AI - Borsa",
            score=best_score,
        )

    return RouteResult(
        area="Genel",
        intent="genel_soru",
        obsidian_keys=["AnaSayfa"],
        confidence=0.4,
    )
