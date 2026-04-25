from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str | None = None
    message: str
    save_to_long_term: bool = True
    include_reflection_context: bool = False
    context_scope: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)
    file_names: list[str] = Field(default_factory=list)
    recent_documents: list[dict[str, object]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    user_id: str
    reply: str
    memory_size: int
    context_hits: int = 0
    doc_context_hits: int = 0
    doc_sources: list[str] = Field(default_factory=list)
    matched_source_ids: list[str] = Field(default_factory=list)
    matched_file_names: list[str] = Field(default_factory=list)
    citations: list[dict[str, object]] = Field(default_factory=list)
    retrieval_fallback_used: bool = False


class CorrectionRequest(BaseModel):
    user_id: str | None = None
    original_answer: str
    corrected_answer: str
    note: str | None = None


class CorrectionResponse(BaseModel):
    status: str
    user_id: str
    correction_id: str


class LongTermMemoryItem(BaseModel):
    id: str
    user_id: str
    kind: str
    text: str
    source: str
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeNode(BaseModel):
    id: str
    weight: int


class KnowledgeEdge(BaseModel):
    source: str
    target: str
    relation: str = "co_occurs"
    weight: int


class KnowledgeGraphResponse(BaseModel):
    user_id: str
    nodes: list[KnowledgeNode]
    edges: list[KnowledgeEdge]


class IngestResponse(BaseModel):
    status: str
    file: str
    chunks: int
    method: str
    collection: str
    content_type: str
    source_id: str | None = None
    document_id: str | None = None
    file_name: str | None = None
    original_file_name: str | None = None
    normalized_file_name: str | None = None
    mime_type: str | None = None
    source_type: str | None = None
    upload_time: str | None = None
    uploaded_at: str | None = None
    chunk_count: int | None = None
    checksum: str | None = None
    user_id: str | None = None
    category: str
    tags: list[str] = Field(default_factory=list)


class ConsolidationRunRequest(BaseModel):
    user_id: str | None = None


class ConsolidationRunResponse(BaseModel):
    status: str
    user_id: str | None = None
    processed_users: int = 0
    summaries_created: int = 0


class DbHealthResponse(BaseModel):
    status: str
    detail: str


class LearningConversationIngestRequest(BaseModel):
    text: str
    role: str = "user"
    source: str = "manual_conversation_ingest"
    save_vector_memory: bool = True


class LearningIngestResponse(BaseModel):
    status: str
    details: dict[str, object] = Field(default_factory=dict)


class LearningConceptItem(BaseModel):
    term: str
    kind: str
    score: float
    frequency: int


class LearningGraphEdgeItem(BaseModel):
    source: str
    relation: str
    target: str
    weight: int


class LearningGraphResponse(BaseModel):
    user_id: str
    nodes: list[LearningConceptItem]
    edges: list[LearningGraphEdgeItem]


class LearningClusterItem(BaseModel):
    cluster_id: str
    label: str
    size: int
    score: float
    terms: list[str] = Field(default_factory=list)
    generated_at: str = ""


class ScoredMemoryItem(BaseModel):
    id: str
    user_id: str
    kind: str
    text: str
    source: str
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)
    importance_score: float
    score_signals: dict[str, float] = Field(default_factory=dict)


class ReflectionRunResponse(BaseModel):
    status: str
    user_id: str
    stored_count: int = 0
    generated_kinds: list[str] = Field(default_factory=list)
    source_counts: dict[str, int] = Field(default_factory=dict)


class ReflectionSummaryResponse(BaseModel):
    user_id: str
    summary: str
    generated_at: str
    user_preferences: str = ""
    stable_rules: str = ""
    project_focus: str = ""
    recurring_topics: str = ""
    concept_clusters: str = ""
