from app.config import settings
from app.rag.search import DocumentHit, _rerank_hits


def _make_hit(source_id: str, index: int) -> DocumentHit:
    return DocumentHit(
        text=f"{source_id} chunk {index}",
        source_id=source_id,
        document_id=source_id,
        original_file_name=f"{source_id}.txt",
        normalized_file_name=f"{source_id}.txt",
        mime_type="text/plain",
        source_type="document",
        category="general",
        method="plain_text",
        upload_time="",
        distance=0.1,
    )


def _run_rerank(hits: list[DocumentHit], n_results: int) -> tuple[list[DocumentHit], dict[str, object]]:
    return _rerank_hits(
        hits=hits,
        n_results=n_results,
        requested_source_ids=set(),
        requested_file_names=set(),
        recent_source_ids=set(),
        recent_file_names=set(),
        query_file_names=set(),
        prefer_recent=False,
        similarity_threshold=None,
    )


def test_default_per_source_cap_for_top_k_12(monkeypatch):
    monkeypatch.setattr(settings, "rag_per_source_cap_min", 2)
    monkeypatch.setattr(settings, "rag_per_source_cap_max", 4)
    hits = [_make_hit(source_id, idx) for source_id in ("s1", "s2", "s3", "s4") for idx in range(10)]

    selected, debug = _run_rerank(hits=hits, n_results=12)

    assert len(selected) == 12
    assert debug["per_source_cap"] == 4
    assert debug["per_source_cap_config"] == {"min": 2, "max": 4}
    assert all(count <= 4 for count in debug["selected_source_distribution"].values())


def test_per_source_cap_respects_configured_max(monkeypatch):
    monkeypatch.setattr(settings, "rag_per_source_cap_min", 1)
    monkeypatch.setattr(settings, "rag_per_source_cap_max", 2)
    hits = [_make_hit(source_id, idx) for source_id in ("s1", "s2", "s3") for idx in range(10)]

    selected, debug = _run_rerank(hits=hits, n_results=6)

    assert len(selected) == 6
    assert debug["per_source_cap"] == 2
    assert debug["per_source_cap_config"] == {"min": 1, "max": 2}
    assert all(count <= 2 for count in debug["selected_source_distribution"].values())


def test_single_source_relaxes_cap(monkeypatch):
    monkeypatch.setattr(settings, "rag_per_source_cap_min", 1)
    monkeypatch.setattr(settings, "rag_per_source_cap_max", 1)
    hits = [_make_hit("only_source", idx) for idx in range(10)]

    selected, debug = _run_rerank(hits=hits, n_results=5)

    assert len(selected) == 5
    assert debug["per_source_cap"] == 5
    assert debug["selected_source_distribution"] == {"only_source": 5}
