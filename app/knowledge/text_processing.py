import re


STOPWORDS = {
    "ve",
    "ile",
    "ama",
    "fakat",
    "icin",
    "gibi",
    "kadar",
    "bir",
    "bu",
    "su",
    "that",
    "with",
    "from",
    "about",
    "uses",
    "use",
    "requires",
    "need",
    "needs",
    "improves",
    "improve",
    "causes",
    "cause",
    "part",
    "parts",
}


TOKEN_PATTERN = re.compile(r"[0-9A-Za-zÇĞİÖŞÜçğıöşü_]{4,}")


def normalize_token(token: str) -> str:
    return token.strip().lower()


def extract_concepts(text: str) -> list[str]:
    concepts: list[str] = []
    seen: set[str] = set()
    for match in TOKEN_PATTERN.finditer(text):
        token = normalize_token(match.group(0))
        if token in STOPWORDS or token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        concepts.append(token)
    return concepts


def extract_concepts_with_positions(text: str) -> list[tuple[str, int]]:
    seen: set[str] = set()
    output: list[tuple[str, int]] = []
    for match in TOKEN_PATTERN.finditer(text):
        token = normalize_token(match.group(0))
        if token in STOPWORDS or token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        output.append((token, match.start()))
    return output
