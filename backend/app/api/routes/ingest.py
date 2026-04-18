"""/ingest —— 上传文档、触发异步 Pipeline。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from app.core.security import Principal, PrincipalDep
from app.ingestion.pipeline import run_ingest_job
from app.models.schemas import IngestJob, IngestStatus

router = APIRouter()


@router.post("/ingest", response_model=IngestJob)
async def ingest(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    source: str = Form("upload"),
    principal: Principal = PrincipalDep,
):
    job_id = uuid.uuid4().hex
    job = IngestJob(job_id=job_id, tenant=principal.tenant, source=source,
                    status=IngestStatus.queued, docs_total=1)
    blob = await file.read()
    background.add_task(run_ingest_job, job, file.filename, blob)
    return job


@router.get("/ingest/{job_id}", response_model=IngestJob)
async def ingest_status(job_id: str):
    from app.ingestion.pipeline import get_job_status
    return await get_job_status(job_id)
