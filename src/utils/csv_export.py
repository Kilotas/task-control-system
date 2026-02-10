import csv
from io import StringIO
from typing import Any


def create_batches_csv(batches: list[dict[str, Any]]) -> bytes:
    """Создает CSV файл со списком партий"""
    output = StringIO()

    fieldnames = [
        "id", "batch_number", "batch_date", "nomenclature", "ekn_code",
        "work_center", "work_center_identifier", "shift", "team",
        "task_description", "shift_start", "shift_end", "is_closed",
        "closed_at", "created_at"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for batch in batches:
        writer.writerow({
            "id": batch["id"],
            "batch_number": batch["batch_number"],
            "batch_date": batch["batch_date"],
            "nomenclature": batch["nomenclature"],
            "ekn_code": batch["ekn_code"],
            "work_center": batch["work_center"],
            "work_center_identifier": batch["work_center_identifier"],
            "shift": batch["shift"],
            "team": batch["team"],
            "task_description": batch["task_description"],
            "shift_start": batch["shift_start"],
            "shift_end": batch["shift_end"],
            "is_closed": "Yes" if batch["is_closed"] else "No",
            "closed_at": batch["closed_at"],
            "created_at": batch["created_at"]
        })

    return output.getvalue().encode("utf-8")