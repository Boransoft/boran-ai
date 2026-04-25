from app.rag import search as rag_search


def _contains_user_scope(where: object, user_id: str) -> bool:
    if isinstance(where, list):
        return any(_contains_user_scope(item, user_id) for item in where)
    if not isinstance(where, dict):
        return False
    if where.get("user_id") == user_id:
        return True
    for key, value in where.items():
        if key in {"$and", "$or"} and isinstance(value, list):
            if any(_contains_user_scope(item, user_id) for item in value):
                return True
        elif isinstance(value, dict):
            if _contains_user_scope(value, user_id):
                return True
    return False


def test_search_docs_blocks_missing_user_scope():
    result = rag_search.search_docs_with_metadata(
        query="raporu ozetle",
        n_results=3,
        user_id=None,
    )
    assert result.hits == []
    assert result.debug.get("reason") == "missing_user_scope"
    assert result.debug.get("doc_context_hits") == 0


def test_build_where_keeps_user_scope_with_explicit_filters():
    where = rag_search._build_where(
        user_id="user_a",
        source_ids=["src_1"],
        normalized_file_names=["report.pdf"],
        raw_file_names=["report.pdf"],
    )
    assert where is not None
    assert _contains_user_scope(where, "user_a")


def test_stage_queries_always_include_user_scope(monkeypatch):
    captured_where: list[dict[str, object] | None] = []

    def fake_query_collection(
        query: str,
        collection_name: str,
        n_results: int = 3,
        where: dict[str, object] | None = None,
    ) -> dict[str, object]:
        captured_where.append(where)
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    monkeypatch.setattr(rag_search, "query_collection", fake_query_collection)
    monkeypatch.setattr(rag_search, "list_recent_document_sources", lambda user_id, limit=8: [])

    result = rag_search.search_docs_with_metadata(
        query="report.pdf icindeki ozeti ver",
        n_results=4,
        user_id="user_a",
        source_ids=["src_1"],
        file_names=["report.pdf"],
        recent_documents=[{"source_id": "src_1", "file_name": "report.pdf"}],
    )

    assert result.hits == []
    assert captured_where
    assert all(where is not None for where in captured_where)
    assert all(_contains_user_scope(where, "user_a") for where in captured_where if where is not None)
