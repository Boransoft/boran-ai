from __future__ import annotations

from pathlib import Path

from app.config import settings


OBSIDIAN_FILE_MAP = {
    "AnaSayfa": ["00-Anasayfa/AnaSayfa.md"],

    "Boran.ai": ["01-BoranAI/Boran.ai.md"],
    "BoranAI Kavramlari": ["01-BoranAI/01-Hafiza/BoranAI Kavramlari.md"],
    "ChatGPT": ["01-BoranAI/01-Hafiza/ChatGPT.md"],
    "NotebookLM": ["01-BoranAI/01-Hafiza/NotebookLM.md"],
    "Obsidian": ["01-BoranAI/01-Hafiza/Obsidian.md"],
    "Vektor Hafiza": ["01-BoranAI/01-Hafiza/Vektor Hafiza.md"],
    "Hafiza Sistemi": ["01-BoranAI/01-Hafiza/Hafiza Sistemi.md"],
    "Mobil Asistan": ["01-BoranAI/01-Hafiza/Mobil Asistan.md"],
    "PDF Ogrenme": ["01-BoranAI/01-Hafiza/PDF Ogrenme.md"],
    "PDF Ogrenme Sistemi": ["01-BoranAI/01-Hafiza/PDF Ogrenme Sistemi.md"],
    "Obsidian ChatGPT Baglantisi": ["01-BoranAI/01-Hafiza/Obsidian ChatGPT Baglantisi.md"],
    "LLM Wiki": ["01-BoranAI/01-Hafiza/LLM Wiki.md"],
    "Markdown Wiki": ["01-BoranAI/01-Hafiza/Markdown Wiki.md"],

    "Is": ["02-Is/Is.md"],
    "Akilli Durak": [
        "02-Is/Akilli Durak/Akilli Durak.md",
        "02-Is/Akilli Durak.md",
    ],
    "Muayene Kabul": [
        "02-Is/Muayene Kabul/Muayene Kabul.md",
        "02-Is/Muayene Kabul.md",
    ],
    "Otobus Alimi": [
        "02-Is/Otobus Alimi/Otobus Alimi.md",
        "02-Is/Otobus Alimi.md",
    ],
    "Sartnameler": [
        "02-Is/Sartnameler/Sartnameler.md",
        "02-Is/Sartnameler.md",
    ],
    "Sozlesmeler": [
        "02-Is/Sozlesmeler/Sozlesmeler.md",
        "02-Is/Sozlesmeler.md",
    ],

    "Portfoy": ["03-Borsa/Portfoy Notlari/Portfoy.md"],

    "Havas": ["04-Havas/Havas.md"],
    "Havas Kavramlari": ["04-Havas/Kavramlar/Havas Kavramlari.md"],
    "Ebced": ["04-Havas/Kavramlar/Ebced.md"],
    "Esmalar": ["04-Havas/Kavramlar/Esmalar.md"],
    "Vefkler": ["04-Havas/Kavramlar/Vefkler.md"],
    "Harfler": ["04-Havas/Kavramlar/Harfler.md"],
    "Sayilar": ["04-Havas/Kavramlar/Sayilar.md"],
    "Terkipler": ["04-Havas/Kavramlar/Terkipler.md"],
    "Insan-i Kamil": ["04-Havas/Kavramlar/Insan-i Kamil.md"],
    "Fususu'l Hikem": ["04-Havas/Kavramlar/Fususu'l Hikem.md"],
    "Muhyiddin Ibn Arabi Risaleleri": ["04-Havas/Kavramlar/Muhyiddin Ibn Arabi Risaleleri.md"],

    "Arsiv": ["05-Arsiv/Arsiv.md"],
}


def _read_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def build_obsidian_context(keys: list[str]) -> str:
    if not settings.obsidian_context_enabled:
        return ""

    vault_raw = (settings.obsidian_vault_path or "").strip()
    if not vault_raw:
        return ""

    vault_path = Path(vault_raw)
    if not vault_path.exists():
        return ""

    max_chars = max(1000, int(settings.obsidian_context_max_chars))
    parts: list[str] = []
    seen_paths: set[str] = set()

    for key in keys:
        rel_paths = OBSIDIAN_FILE_MAP.get(key, [])

        for rel_path in rel_paths:
            full_path = vault_path / rel_path
            full_key = str(full_path)

            if full_key in seen_paths:
                continue

            seen_paths.add(full_key)
            content = _read_file(full_path)

            if not content.strip():
                continue

            parts.append(
                f"\n\n[Obsidian Context: {key} | {rel_path}]\n{content.strip()}"
            )

            joined = "\n".join(parts)
            if len(joined) >= max_chars:
                return joined[:max_chars] + "\n\n[Obsidian context truncated]"

    return "\n".join(parts)


def debug_obsidian_files(keys: list[str]) -> list[dict[str, object]]:
    vault_raw = (settings.obsidian_vault_path or "").strip()
    vault_path = Path(vault_raw) if vault_raw else None

    results: list[dict[str, object]] = []

    for key in keys:
        for rel_path in OBSIDIAN_FILE_MAP.get(key, []):
            full_path = vault_path / rel_path if vault_path else Path(rel_path)
            results.append(
                {
                    "key": key,
                    "relative_path": rel_path,
                    "full_path": str(full_path),
                    "exists": full_path.exists() if vault_path else False,
                }
            )

    return results
