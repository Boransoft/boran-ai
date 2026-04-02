from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str | None = None
    message: str
    save_to_long_term: bool = True
    include_reflection_context: bool = False


class ChatResponse(BaseModel):
    user_id: str
    reply: str
    memory_size: int
    context_hits: int = 0


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
