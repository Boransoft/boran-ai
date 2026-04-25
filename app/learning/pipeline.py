from dataclasses import dataclass

from app.ingest.service import ingest_file_with_text
from app.learning.clustering import concept_cluster_engine
from app.learning.concepts import ExtractionResult
from app.learning.extractor import concept_extractor
from app.learning.graph import learning_graph_store
from app.learning.graph_relations import graph_relation_engine, merge_relations
from app.learning.semantic_linking import semantic_linker
from app.memory.long_term import long_term_memory
from app.rag.conversation_memory import save_conversation


@dataclass
class LearningPipelineResult:
    status: str
    details: dict[str, object]


def _compact_text(text: str, max_chars: int = 1800) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


class LearningPipeline:
    def _run_learning_enrichment(
        self,
        user_id: str,
        text: str,
    ) -> dict[str, int]:
        extraction = concept_extractor.extract(text)
        enriched = graph_relation_engine.enrich(text=text, extraction=extraction)

        semantic_relations = semantic_linker.build_semantic_relations(
            user_id=user_id,
            terms=[concept.term for concept in enriched.concepts],
        )
        enriched = ExtractionResult(
            concepts=enriched.concepts,
            relations=merge_relations(enriched.relations + semantic_relations),
        )

        graph_delta = learning_graph_store.update_from_extraction(user_id, enriched)
        cluster_state = concept_cluster_engine.refresh_user_clusters(user_id=user_id)
        graph_delta["clusters_added"] = int(cluster_state.get("inserted", 0))
        graph_delta["clusters_total"] = len(cluster_state.get("clusters", []))
        return graph_delta

    def ingest_document(
        self,
        user_id: str,
        file_path: str,
        category: str = "general",
        tags: str | list[str] | None = None,
    ) -> LearningPipelineResult:
        ingest_output = ingest_file_with_text(
            file_path=file_path,
            category=category,
            tags=tags,
            user_id=user_id,
        )
        result = ingest_output.result
        text = ingest_output.text
        if result.get("status") != "ok":
            return LearningPipelineResult(status="error", details=result)

        if text.strip():
            long_term_memory.add(
                user_id=user_id,
                text=_compact_text(text),
                kind="semantic_document",
                source=str(result.get("source_id", result.get("file", file_path))),
                metadata={
                    "source_id": str(result.get("source_id", "")),
                    "document_id": str(result.get("document_id", "")),
                    "file_name": str(result.get("original_file_name", "")),
                    "content_type": str(result.get("content_type", "unknown")),
                    "category": str(result.get("category", category)),
                },
            )
            graph_delta = self._run_learning_enrichment(user_id=user_id, text=text)
        else:
            graph_delta = {
                "concepts_added": 0,
                "edges_added": 0,
                "clusters_added": 0,
                "clusters_total": 0,
            }

        details = dict(result)
        details.update(graph_delta)
        return LearningPipelineResult(status="ok", details=details)

    def ingest_conversation(
        self,
        user_id: str,
        role: str,
        text: str,
        source: str = "conversation",
        save_vector_memory: bool = True,
    ) -> LearningPipelineResult:
        if not text.strip():
            return LearningPipelineResult(status="error", details={"message": "Empty text."})

        if save_vector_memory:
            save_conversation(user_id=user_id, role=role, text=text)

        long_term_memory.add(
            user_id=user_id,
            text=_compact_text(text),
            kind="semantic_conversation",
            source=source,
            metadata={"role": role},
        )

        graph_delta = self._run_learning_enrichment(user_id=user_id, text=text)

        return LearningPipelineResult(
            status="ok",
            details={
                "role": role,
                "source": source,
                "concepts_added": graph_delta["concepts_added"],
                "edges_added": graph_delta["edges_added"],
                "clusters_added": graph_delta["clusters_added"],
                "clusters_total": graph_delta["clusters_total"],
            },
        )


learning_pipeline = LearningPipeline()
