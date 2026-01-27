from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.application.uow.protocol import UnitOfWorkProtocol
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
)

from src.data.models.product import Product

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, uow: UnitOfWorkProtocol):
        self.uow = uow

    async def create_product(self, data: dict[str, Any]) -> Product:
        logger.info(
            "product.create.started",
            unique_code=data["unique_code"],
            batch_id=data["batch_id"],
        )

        async with self.uow as uow:
            batch = await uow.batches.get_by_id(data["batch_id"])
            if batch is None:
                raise NotFoundException("Batch", data["batch_id"])

            exists = await uow.products.exists_by_unique_code(data["unique_code"])
            if exists:
                raise ConflictException(
                    f"Product with unique_code already exists: {data['unique_code']}"
                )

            product = Product(
                unique_code=data["unique_code"],
                batch_id=data["batch_id"],
            )

            try:
                product = await uow.products.create(product)
                await uow.flush()

            except IntegrityError:
                logger.warning(
                    "product.create.integrity_error",
                    unique_code=data["unique_code"],
                )
                raise ConflictException(
                    f"Product with unique_code already exists: {data['unique_code']}"
                )

            logger.info(
                "product.create.success",
                product_id=product.id,
                batch_id=product.batch_id,
            )

            return product