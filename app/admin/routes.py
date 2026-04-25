from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.admin.service import admin_data_service
from app.auth.routes import get_current_admin_external_id


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def admin_dashboard(_: str = Depends(get_current_admin_external_id)):
    return admin_data_service.dashboard()


@router.get("/documents")
def admin_documents(
    status: str = Query(default=""),
    q: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_documents(status=status, query=q, limit=limit, offset=offset)


@router.get("/documents/{document_id}")
def admin_document_detail(
    document_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.get_document_detail(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/documents/{document_id}/reprocess")
def admin_document_reprocess(
    document_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.reprocess_document(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/documents/{document_id}")
def admin_document_delete(
    document_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.delete_document(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/documents/bulk-delete")
def admin_documents_bulk_delete(
    document_ids: list[str] = Body(default=[]),
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.bulk_delete_documents(document_ids=document_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/documents/bulk-reprocess")
def admin_documents_bulk_reprocess(
    document_ids: list[str] = Body(default=[]),
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.bulk_reprocess_documents(document_ids=document_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ingest-jobs")
def admin_ingest_jobs(
    status: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_ingest_jobs(status=status, limit=limit, offset=offset)


@router.post("/ingest-jobs/{job_id}/retry")
def admin_retry_ingest_job(
    job_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.retry_ingest_job(job_id=job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/ingest-jobs/retry-failed")
def admin_retry_failed_ingest_jobs(
    limit: int = Query(default=10, ge=1, le=100),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.retry_failed_ingest_jobs(limit=limit)


@router.get("/conversations")
def admin_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_conversations(limit=limit, offset=offset)


@router.delete("/conversations/{conversation_id}")
def admin_delete_conversation(
    conversation_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.delete_conversation(conversation_id=conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/conversations/{conversation_id}/messages")
def admin_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=8, ge=1, le=100),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_conversation_messages(conversation_id=conversation_id, limit=limit)


@router.get("/logs")
def admin_logs(
    level: str = Query(default=""),
    component: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_logs(level=level, component=component, limit=limit, offset=offset)


@router.post("/logs/clear")
def admin_logs_clear(
    level: str = Query(default=""),
    component: str = Query(default=""),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.clear_logs(level=level, component=component)


@router.get("/logs/{log_id}")
def admin_log_detail(
    log_id: str,
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.get_log_detail(log_id=log_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/chunks/summary")
def admin_chunk_summary(
    limit: int = Query(default=50, ge=1, le=300),
    _: str = Depends(get_current_admin_external_id),
):
    return admin_data_service.list_chunk_summary(limit=limit)


@router.get("/chunks/{document_id}/samples")
def admin_chunk_samples(
    document_id: str,
    limit: int = Query(default=6, ge=1, le=50),
    _: str = Depends(get_current_admin_external_id),
):
    try:
        return admin_data_service.list_chunk_samples(document_id=document_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
