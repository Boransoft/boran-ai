from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

import requests

from app.config import settings
from app.services.context_router import RouteResult


LLM_CONTEXT_MAX_CHARS = 3500

SYSTEM_PROMPT = (
    "Sen Boran.ai adli kisisel asistansin. Turkce cevap ver. "
    "Obsidian context belge deposu degildir; sadece yon ve baglam haritasidir. "
    "Verilen Obsidian baglamini yalnizca alan/kategori yonlendirmesi olarak kullan. "
    "Boran.ai mimari, mobil uygulama, NotebookLM, Obsidian, backend, hafiza, "
    "vektor hafiza, PDF ogrenme veya sistem karari sorularinda gercek belge/RAG "
    "sonucu olmasa bile Obsidian baglamina dayanarak mimari cevap verebilirsin. "
    "Kullanici 'sartname maddelerini getir', 'sozlesme maddelerini getir', "
    "'teknik maddeyi getir' veya 'belgedeki maddeyi getir' diyorsa ve gercek belge "
    "metni/RAG sonucu yoksa madde uydurma. LED panel tipi, guc tuketimi, "
    "IP koruma sinifi gibi ornek teknik madde listeleme. "
    "Bunun yerine aynen sunu soyle: Bu soru Is / Akilli Durak / Sartnameler alanina "
    "yonlendirildi. Ancak gercek sartname belgesi taranmadan LED panel maddeleri "
    "kesin olarak getirilemez. "
    "Obsidian'da sadece alan/kategori bilgisi varsa teknik icerik uretme. "
    "Havas icin kaynakta gecmeyen tilsim, esma tertibi, vefk veya uygulama uretme; "
    "sadece bu soru Havas/Terkipler/Esmalar alanina yonlenir ve kaynak belge taramasi "
    "gerekir seklinde cevap ver. Kisa, net ve guvenli cevap ver."
)


@dataclass
class LLMAnswer:
    reply: str
    used_llm: bool
    error: str = ""
    fallback_reason: str = ""


@dataclass
class LLMHealth:
    ready: bool
    error: str = ""
    model: str = settings.model_name
    base_url: str = settings.lm_studio_base_url
    fallback_reason: str = ""


def _is_render_runtime() -> bool:
    return any(
        os.getenv(name)
        for name in (
            "RENDER",
            "RENDER_SERVICE_ID",
            "RENDER_SERVICE_NAME",
            "RENDER_EXTERNAL_HOSTNAME",
        )
    )


def _is_local_lm_studio_url(base_url: str) -> bool:
    try:
        hostname = (urlparse(base_url).hostname or "").lower()
    except Exception:
        return False
    return hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def local_lm_studio_unavailable_reason() -> str:
    if _is_render_runtime() and _is_local_lm_studio_url(settings.lm_studio_base_url):
        return "local_lm_studio_not_reachable_from_render"
    return ""


def check_lm_studio_health(timeout: float = 3.0) -> LLMHealth:
    fallback_reason = local_lm_studio_unavailable_reason()
    if fallback_reason:
        return LLMHealth(
            ready=False,
            error="llm_unavailable_on_render",
            fallback_reason=fallback_reason,
        )

    try:
        response = requests.get(
            f"{settings.lm_studio_base_url}/models",
            timeout=min(max(timeout, 1.0), 3.0),
        )
        response.raise_for_status()
        return LLMHealth(ready=True)
    except Exception as exc:
        return LLMHealth(ready=False, error=str(exc))


def _llm_timeout_seconds() -> float:
    return max(1.0, float(settings.chat_llm_timeout_seconds))


def _build_prompt(message: str, route: RouteResult, obsidian_context: str, document_context: str = "") -> str:
    safe_obsidian_context = obsidian_context[:LLM_CONTEXT_MAX_CHARS]
    safe_document_context = document_context[:LLM_CONTEXT_MAX_CHARS]
    obsidian = safe_obsidian_context.strip()
    document = safe_document_context.strip()
    if not document:
        document = "[Kaynak belge bulunamadi.]"

    concepts = ", ".join(route.concepts) if route.concepts else "-"
    obsidian_section = f"\nKisaltilmis Obsidian baglami:\n{obsidian}\n" if obsidian else ""

    return (
        f"Kullanici sorusu:\n{message}\n\n"
        f"Alan: {route.area}\n"
        f"Konu: {route.topic or '-'}\n"
        f"Niyet: {route.intent or '-'}\n"
        f"Kavramlar: {concepts}\n\n"
        f"{obsidian_section}"
        f"Kaynak belge parcasi:\n{document}"
    )


def build_lm_studio_fallback(
    message: str,
    route: RouteResult,
    obsidian_context: str,
    error: Exception | str,
    document_context: str = "",
) -> str:
    fallback_reason = local_lm_studio_unavailable_reason()
    document_snippet = document_context.strip()
    if len(document_snippet) > 900:
        document_snippet = document_snippet[:900].rstrip() + "..."

    obsidian_snippet = obsidian_context.strip()
    if len(obsidian_snippet) > 500:
        obsidian_snippet = obsidian_snippet[:500].rstrip() + "..."

    if route.area == "Boran.ai" and obsidian_snippet:
        return (
            "Model şu anda bağlı değil. Sistem çalışıyor ve Boran.ai sorusu Obsidian bağlamına yönlendirildi.\n\n"
            "Kısa cevap: Obsidian bu projede belge deposu yerine yön ve bağlam haritası gibi çalışmalı. "
            "PDF öğrenme mimarisi ise yüklenen belgeleri parçalayıp vektör belleğe kaydetmeli, chat sırasında "
            "yalnızca ilgili kaynak parçalarını RAG bağlamı olarak kullanmalı ve kaynak yoksa madde uydurmamalı."
        )

    if document_snippet:
        return (
            "Model şu anda bağlı değil. Sistem belge bağlamı buldu ancak AI yanıtı üretilemedi.\n\n"
            f"Kaynak parçadan kısa önizleme:\n{document_snippet}"
        )

    reason_text = f" ({fallback_reason})" if fallback_reason else ""
    return f"Model şu anda bağlı değil. Sistem çalışıyor ancak AI yanıtı üretilemedi{reason_text}."


def generate_obsidian_answer(
    message: str,
    route: RouteResult,
    obsidian_context: str,
    document_context: str = "",
) -> LLMAnswer:
    fallback_reason = local_lm_studio_unavailable_reason()
    if fallback_reason:
        error = "llm_unavailable_on_render"
        return LLMAnswer(
            reply=build_lm_studio_fallback(
                message=message,
                route=route,
                obsidian_context=obsidian_context,
                document_context=document_context,
                error=error,
            ),
            used_llm=False,
            error=error,
            fallback_reason=fallback_reason,
        )

    prompt = _build_prompt(
        message=message,
        route=route,
        obsidian_context=obsidian_context,
        document_context=document_context,
    )

    try:
        response = requests.post(
            f"{settings.lm_studio_base_url}/chat/completions",
            json={
                "model": settings.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            },
            timeout=_llm_timeout_seconds(),
        )
        response.raise_for_status()
        data = response.json()
        reply = str(data["choices"][0]["message"]["content"]).strip()
        if not reply:
            raise ValueError("LM Studio bos cevap dondu.")
        return LLMAnswer(reply=reply, used_llm=True)
    except Exception as exc:
        return LLMAnswer(
            reply=build_lm_studio_fallback(
                message=message,
                route=route,
                obsidian_context=obsidian_context,
                document_context=document_context,
                error=exc,
            ),
            used_llm=False,
            error=str(exc),
            fallback_reason="llm_request_failed",
        )
