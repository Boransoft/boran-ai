import hashlib
import logging
import math
import re
import threading
from pathlib import Path

import requests
from sentence_transformers import SentenceTransformer

from app.config import settings


FALLBACK_DIM = 384
TOKEN_PATTERN = re.compile(r"(?u)\b\w{2,}\b")
HF_HOST = "huggingface.co"
logger = logging.getLogger(__name__)

_state_lock = threading.Lock()
_state = {
    "mode": "uninitialized",  # uninitialized | cache | downloaded | fallback_hash
    "model": None,
    "reason": "",
    "resolved_model": "",
}


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _hash_index(token: str) -> int:
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % FALLBACK_DIM


def _fallback_encode(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        vector = [0.0] * FALLBACK_DIM
        for token in _tokenize(text):
            vector[_hash_index(token)] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        vectors.append(vector)
    return vectors


def _can_reach_huggingface(model_name: str, timeout_seconds: float) -> bool:
    url = f"https://{HF_HOST}/api/models/{model_name}"
    try:
        response = requests.get(url, timeout=timeout_seconds)
        return 200 <= response.status_code < 500
    except requests.RequestException:
        return False


def _load_from_local_cache(model_name: str, cache_path: Path) -> SentenceTransformer:
    return SentenceTransformer(
        model_name_or_path=model_name,
        cache_folder=str(cache_path),
        local_files_only=True,
    )


def _load_with_download(model_name: str, cache_path: Path) -> SentenceTransformer:
    return SentenceTransformer(
        model_name_or_path=model_name,
        cache_folder=str(cache_path),
        local_files_only=False,
    )


def _resolve_model_name() -> str:
    model_name = settings.embedding_model.strip()
    if "/" not in model_name:
        return f"sentence-transformers/{model_name}"
    return model_name


def _initialize_encoder() -> None:
    with _state_lock:
        if _state["mode"] != "uninitialized":
            return

        model_name = _resolve_model_name()
        _state["resolved_model"] = model_name
        cache_path = Path(settings.embedding_cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)

        if any(cache_path.iterdir()):
            try:
                model = _load_from_local_cache(model_name=model_name, cache_path=cache_path)
                _state["model"] = model
                _state["mode"] = "cache"
                _state["reason"] = "loaded from local cache"
                return
            except Exception as cache_exc:
                cache_reason = f"cache miss or cache load error: {cache_exc}"
        else:
            cache_reason = "cache path is empty"

        if settings.embedding_allow_download and _can_reach_huggingface(
            model_name=model_name,
            timeout_seconds=settings.embedding_download_timeout_seconds,
        ):
            try:
                model = _load_with_download(model_name=model_name, cache_path=cache_path)
                _state["model"] = model
                _state["mode"] = "downloaded"
                _state["reason"] = "downloaded and cached"
                return
            except Exception as download_exc:
                _state["mode"] = "fallback_hash"
                _state["reason"] = f"download failed: {download_exc}"
                logger.warning("Embedding model fallback enabled. Reason: %s", _state["reason"])
                return

        _state["mode"] = "fallback_hash"
        _state["reason"] = cache_reason + "; no internet/download disabled"
        logger.warning("Embedding model fallback enabled. Reason: %s", _state["reason"])


def get_embedding_backend_info() -> dict[str, str]:
    _initialize_encoder()
    return {
        "mode": str(_state["mode"]),
        "model": str(_state["resolved_model"]) or _resolve_model_name(),
        "cache_path": settings.embedding_cache_path,
        "reason": str(_state["reason"]),
    }


def encode_texts(texts: list[str]) -> list[list[float]]:
    _initialize_encoder()

    model = _state["model"]
    if model is not None:
        try:
            return model.encode(texts).tolist()
        except Exception as exc:
            logger.warning("Embedding encode failed, fallback hash used. Reason: %s", exc)
            return _fallback_encode(texts)

    return _fallback_encode(texts)
