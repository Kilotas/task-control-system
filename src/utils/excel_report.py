from __future__ import annotations

import csv
import io
from openpyxl import Workbook

from src.domain.dto.export_dto import BatchExportRowDTO


EXCEL_HEADERS = [
    "ID", "НомерПартии", "ДатаПартии", "СтатусЗакрытия", "ДатаЗакрытия",
    "ИдентификаторРЦ", "РабочийЦентр", "Смена", "Бригада", "Номенклатура",
    "КодЕКН", "НачалоСмены", "ОкончаниеСмены",
]


def export_batches_to_excel(rows: list[BatchExportRowDTO]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Batches"

    ws.append(EXCEL_HEADERS)

    for r in rows:
        ws.append([
            r.id,
            r.batch_number,
            str(r.batch_date),
            bool(r.is_closed),
            str(r.closed_at) if r.closed_at else "",
            r.work_center_identifier or "",
            r.work_center_name or "",
            r.shift or "",
            r.team or "",
            r.nomenclature or "",
            r.ekn_code or "",
            str(r.shift_start) if r.shift_start else "",
            str(r.shift_end) if r.shift_end else "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_batches_to_csv(rows: list[BatchExportRowDTO]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXCEL_HEADERS)

    for r in rows:
        writer.writerow([
            r.id,
            r.batch_number,
            str(r.batch_date),
            bool(r.is_closed),
            str(r.closed_at) if r.closed_at else "",
            r.work_center_identifier or "",
            r.work_center_name or "",
            r.shift or "",
            r.team or "",
            r.nomenclature or "",
            r.ekn_code or "",
            str(r.shift_start) if r.shift_start else "",
            str(r.shift_end) if r.shift_end else "",
        ])

    return buf.getvalue().encode("utf-8")
