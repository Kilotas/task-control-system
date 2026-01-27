from typing import Annotated

from fastapi import APIRouter, status, Depends

from src.api.v1.schemas.batch import BatchCreateIn, BatchCreatedOut, BatchDetailOut, BatchUpdateIn, BatchListQuery, BatchAggregateOut
from src.core.dependencies import BatchServiceDep
from src.api.v1.mappers.batch_mapper import to_created_out

from src.api.v1.schemas.task import AggregateAsyncIn, TaskStartedOut
from src.tasks.aggregation import aggregate_products_batch

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post(
    "",
    response_model=list[BatchCreatedOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_batches(
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

