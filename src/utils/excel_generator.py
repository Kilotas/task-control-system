from __future__ import annotations

import io
from openpyxl import Workbook

from src.domain.dto.report_dto import BatchReportDTO


def generate_batch_report(batch: BatchReportDTO) -> bytes:
    """
    Генерирует Excel отчёт по партии и возвращает bytes (без записи на диск).
    batch: ORM объект Batch с загруженными products и work_center.
    """
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Информация о партии"

    ws1.append(["Номер партии", batch.batch_number])
    ws1.append(["Дата партии", str(batch.batch_date)])
    ws1.append(["Статус", "Закрыта" if batch.is_closed else "Открыта"])
    wc_name = batch.work_center.name if getattr(batch, "work_center", None) else "-"
    ws1.append(["Рабочий центр", wc_name])
    ws1.append(["Смена", batch.shift])
    ws1.append(["Бригада", batch.team])
    ws1.append(["Номенклатура", batch.nomenclature])
    ws1.append(["Начало смены", str(batch.shift_start)])
    ws1.append(["Окончание смены", str(batch.shift_end)])

    ws2 = wb.create_sheet("Продукция")
    ws2.append(["ID", "Уникальный код", "Аггрегирована", "Дата аггрегации"])
    for p in batch.products:
        ws2.append([
            p.id,
            p.unique_code,
            "Да" if p.is_aggregated else "Нет",
            str(p.aggregated_at) if p.aggregated_at else "-",
        ])

    ws3 = wb.create_sheet("Статистика")
    total = len(batch.products)
    aggregated = sum(1 for p in batch.products if p.is_aggregated)
    remaining = total - aggregated
    percent = int((aggregated / total) * 100) if total else 0
    ws3.append(["Всего продукции", total])
    ws3.append(["Аггрегировано", aggregated])
    ws3.append(["Осталось", remaining])
    ws3.append(["Процент выполнения", f"{percent}%"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
