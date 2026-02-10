from typing import Annotated

from fastapi import APIRouter, status, Depends, UploadFile, File, Request

from src.api.v1.schemas.batch import BatchCreateIn, BatchCreatedOut, BatchDetailOut, BatchUpdateIn, BatchListQuery, BatchAggregateOut
from src.api.v1.schemas.export import BatchExportIn
from src.api.v1.schemas.reports import BatchReportIn
from src.core.dependencies import BatchServiceDep
from src.core.rate_limiter import limiter
from src.domain.mappers.batch_mapper import to_created_out

from src.api.v1.schemas.task import AggregateAsyncIn, TaskStartedOut
from src.tasks.aggregation import aggregate_products_batch
from src.tasks.reports import generate_batch_report
from src.storage.minio_service import get_minio_service
from src.tasks.imports import import_batches_from_file
from src.tasks.batch_tasks import export_batches_to_file


router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post(
    "",
    response_model=list[BatchCreatedOut],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_batches(
    request: Request,
    payload: list[BatchCreateIn],
    service: BatchServiceDep,
) -> list[BatchCreatedOut]:
    items = [dto.model_dump(by_alias=False) for dto in payload]

    created = await service.create_batches(items)
    return [
        to_created_out(batch, item["work_center_identifier"])
        for batch, item in zip(created, items)
    ]


@router.get(
    "/{batch_id}",
    response_model=BatchDetailOut,
    status_code=status.HTTP_200_OK,
)
async def get_batch_by_id(
    batch_id: int,
    service: BatchServiceDep,
) -> BatchDetailOut:
    batch = await service.get_batch_by_id(batch_id)
    return batch


@router.patch(
    "/{batch_id}",
    response_model=BatchCreatedOut,
    status_code=status.HTTP_200_OK,
)
async def update_batch(
    batch_id: int,
    payload: BatchUpdateIn,
    service: BatchServiceDep,
):
    batch = await service.update_batch(
        batch_id=batch_id,
        data=payload
    )

    return to_created_out(
        batch=batch,
        work_center_identifier=batch.work_center.identifier,
    )


@router.get(
    "",
    response_model=list[BatchCreatedOut],
    status_code=status.HTTP_200_OK,
)
async def list_batches(
    query: Annotated[BatchListQuery, Depends()],
    service: BatchServiceDep,
):
    batches_with_identifiers = await service.list_batches(query)

    return [
        to_created_out(
            batch=b["batch"],
            work_center_identifier=b["work_center_identifier"],
        )
        for b in batches_with_identifiers
    ]


@router.post(
    "/{batch_id}/aggregate",
    response_model=BatchAggregateOut,
    status_code=status.HTTP_200_OK,
)
async def aggregate_batch_products(
    batch_id: int,
    service: BatchServiceDep,
):
    result = await service.aggregate_batch_products(batch_id)
    return result


@router.post(
    "/{batch_id}/aggregate-async",
    response_model=TaskStartedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def aggregate_batch_products_async(
    batch_id: int,
    payload: AggregateAsyncIn,
):
    task = aggregate_products_batch.delay(
        batch_id=batch_id,
        unique_codes=payload.unique_codes,
        user_id=payload.user_id,
    )

    return TaskStartedOut(
        task_id=task.id,
        status=task.status,
        message="Aggregation task started",
    )


@router.post(
    "/{batch_id}/reports",
    response_model=TaskStartedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_batch_report_async(
    batch_id: int,
    payload: BatchReportIn,
):
    task = generate_batch_report.delay(
        batch_id=batch_id,
        format=payload.format,
        user_email=payload.email,
    )

    return TaskStartedOut(
        task_id=task.id,
        status=task.status,
        message="Report generation started",
    )

@router.post(
    "/import",
    response_model=TaskStartedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def import_batches(request: Request, file: UploadFile = File(...)):
    data = await file.read()

    minio = get_minio_service()
    object_name = file.filename or "batches.xlsx"
    await minio.upload_bytes(bucket="imports", object_name=object_name, data=data,
                             content_type=file.content_type or "application/octet-stream")


    task = import_batches_from_file.delay(file_object_name=object_name, user_id=1)

    return TaskStartedOut(task_id=task.id, status=task.status, message="File uploaded, import started")


@router.post(
    "/export",
    response_model=TaskStartedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def export_batches(request: Request, payload: BatchExportIn):
    task = export_batches_to_file.delay(filters=payload.filters, format=payload.format)
    return TaskStartedOut(task_id=task.id, status=task.status, message="Export started")

