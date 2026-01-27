from __future__ import annotations

from fastapi import APIRouter, status

from src.api.v1.schemas.product import ProductCreate, ProductOut
from src.core.dependencies import ProductServiceDep

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductCreate,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate,
    service: ProductServiceDep,
) -> ProductOut:
    data = payload.model_dump(by_alias=False)

    product = await service.create_product(data)


    return product
