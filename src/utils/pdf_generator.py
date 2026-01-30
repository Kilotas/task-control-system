from __future__ import annotations

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def generate_batch_report(*, batch) -> bytes:
    """
    Генерирует PDF отчёт по партии и возвращает bytes (без записи на диск).
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Отчет по партии #{batch.batch_number} (id={batch.id})")
    y -= 24

    wc_name = batch.work_center.name if getattr(batch, "work_center", None) else "-"

    c.setFont("Helvetica", 11)
    lines = [
        f"Дата партии: {batch.batch_date}",
        f"Статус: {'Закрыта' if batch.is_closed else 'Открыта'}",
        f"Рабочий центр: {wc_name}",
        f"Смена: {batch.shift}",
        f"Бригада: {batch.team}",
        f"Номенклатура: {batch.nomenclature}",
        f"Начало смены: {batch.shift_start}",
        f"Окончание смены: {batch.shift_end}",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 16

    total = len(batch.products)
    aggregated = sum(1 for p in batch.products if p.is_aggregated)
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Статистика")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Всего: {total} | Аггрегировано: {aggregated} | Осталось: {total - aggregated}")

    c.showPage()
    c.save()
    return buf.getvalue()
