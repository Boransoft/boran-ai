from sqlalchemy import delete, select

from app.db.models import Conversation, Correction, KnowledgeEdge, MemoryItem, User
from app.db.session import get_session
from app.learning.graph import learning_graph_store
from app.memory.long_term import long_term_memory


def _get_or_create_user_id(session, external_id: str) -> str:
    result = session.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()
    if user:
        return str(user.id)

    user = User(external_id=external_id)
    session.add(user)
    session.flush()
    return str(user.id)


def sync_conversation_message(
    user_external_id: str,
    role: str,
    message_text: str,
    source: str = "chat",
    metadata_json: dict | None = None,
) -> None:
    with get_session() as session:
        user_id = _get_or_create_user_id(session, user_external_id)
        session.add(
            Conversation(
                user_id=user_id,
                role=role,
                message_text=message_text,
                source=source,
                metadata_json=metadata_json or {},
            )
        )
        session.commit()


def sync_memory_item(
    user_external_id: str,
    kind: str,
    text: str,
    source: str,
    metadata_json: dict | None = None,
) -> None:
    with get_session() as session:
        user_id = _get_or_create_user_id(session, user_external_id)
        session.add(
            MemoryItem(
                user_id=user_id,
                kind=kind,
                text=text,
                source=source,
                metadata_json=metadata_json or {},
            )
        )
        session.commit()


def sync_correction(
    user_external_id: str,
    original_answer: str,
    corrected_answer: str,
    note: str | None,
) -> None:
    with get_session() as session:
        user_id = _get_or_create_user_id(session, user_external_id)
        session.add(
            Correction(
                user_id=user_id,
                original_answer=original_answer,
                corrected_answer=corrected_answer,
                note=note,
                status="active",
            )
        )
        session.commit()


def sync_knowledge_edges(user_external_id: str, edges: list[dict[str, int | str]]) -> int:
    with get_session() as session:
        user_id = _get_or_create_user_id(session, user_external_id)
        session.execute(delete(KnowledgeEdge).where(KnowledgeEdge.user_id == user_id))

        for edge in edges:
            session.add(
                KnowledgeEdge(
                    user_id=user_id,
                    source_node=str(edge.get("source", "")),
                    relation=str(edge.get("relation", "co_occurs")),
                    target_node=str(edge.get("target", "")),
                    weight=int(edge.get("weight", 1)),
                    metadata_json={},
                )
            )

        session.commit()
        return len(edges)


def sync_user_snapshot(user_external_id: str) -> dict[str, int]:
    memory_items = long_term_memory.list_user(user_id=user_external_id, limit=5000)
    graph = learning_graph_store.get_graph(user_id=user_external_id, max_nodes=300, max_edges=300)

    synced_memory = 0
    for item in memory_items:
        sync_memory_item(
            user_external_id=user_external_id,
            kind=str(item.get("kind", "memory")),
            text=str(item.get("text", "")),
            source=str(item.get("source", "snapshot")),
            metadata_json=item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {},
        )
        synced_memory += 1

    synced_edges = sync_knowledge_edges(user_external_id=user_external_id, edges=graph["edges"])
    return {
        "memory_items": synced_memory,
        "knowledge_edges": synced_edges,
    }
