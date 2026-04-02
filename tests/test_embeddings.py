from app.rag.embeddings import encode_texts


def test_encode_texts_returns_consistent_vector_shapes():
    vectors = encode_texts(
        [
            "semantic search with vector database",
            "pdf ocr and long term memory",
        ]
    )

    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1])
    assert len(vectors[0]) > 0
