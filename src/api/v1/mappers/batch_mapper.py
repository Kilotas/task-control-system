from src.api.v1.schemas.batch import BatchCreatedOut

def to_created_out(batch, work_center_identifier: str) -> BatchCreatedOut:
    return BatchCreatedOut(
        id=batch.id,
        is_closed=batch.is_closed,
        batch_number=batch.batch_number,
        batch_date=batch.batch_date,
        work_center_identifier=work_center_identifier,
        created_at=batch.created_at,
    )
