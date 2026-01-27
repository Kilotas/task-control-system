from fastapi import APIRouter
from celery.result import AsyncResult

from src.api.v1.schemas.task import TaskStatusOut
from src.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskStatusOut)
async def get_task_status(task_id: str) -> TaskStatusOut:
    res = AsyncResult(task_id, app=celery_app)

    payload = res.info if isinstance(res.info, dict) else None

    return TaskStatusOut(
        task_id=task_id,
        status=res.status,
        result=payload,
    )
