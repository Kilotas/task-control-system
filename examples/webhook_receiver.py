"""
Пример Flask webhook receiver для верификации и обработки событий.

Запуск:
    pip install flask
    WEBHOOK_SECRET=your_secret_key python webhook_receiver.py

Или для production:
    gunicorn -w 4 -b 0.0.0.0:5000 webhook_receiver:app
"""

import hashlib
import hmac
import logging
import os
import time
from functools import wraps

from flask import Flask, request, jsonify, abort

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Секретный ключ для верификации подписи (должен совпадать с secret_key в WebhookSubscription)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your-webhook-secret-key")

# Максимальное время жизни подписи (5 минут)
SIGNATURE_MAX_AGE = 300


def verify_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """
    Верификация HMAC-SHA256 подписи webhook.

    Формат подписи: t={timestamp},v1={signature}

    Args:
        payload: Тело запроса в байтах
        signature_header: Значение заголовка X-Webhook-Signature
        secret: Секретный ключ

    Returns:
        True если подпись валидна, False иначе
    """
    if not signature_header:
        return False

    try:
        elements = {}
        for part in signature_header.split(","):
            key, value = part.split("=", 1)
            elements[key] = value

        timestamp = elements.get("t")
        received_signature = elements.get("v1")

        if not timestamp or not received_signature:
            logger.warning("Missing timestamp or signature in header")
            return False


        current_time = int(time.time())
        signature_time = int(timestamp)

        if abs(current_time - signature_time) > SIGNATURE_MAX_AGE:
            logger.warning(
                "Signature expired: timestamp=%s, current=%s, diff=%ss",
                signature_time, current_time, abs(current_time - signature_time)
            )
            return False

        # Вычисляем ожидаемую подпись
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Сравниваем подписи (timing-safe comparison)
        return hmac.compare_digest(expected_signature, received_signature)

    except (ValueError, KeyError) as e:
        logger.warning("Failed to parse signature header: %s", e)
        return False


def require_webhook_signature(f):
    """Декоратор для верификации подписи webhook."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Webhook-Signature")
        payload = request.get_data()

        if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
            logger.warning(
                "Invalid webhook signature from %s, event=%s",
                request.remote_addr,
                request.headers.get("X-Webhook-Event", "unknown")
            )
            abort(401, description="Invalid webhook signature")

        return f(*args, **kwargs)
    return decorated_function


@app.route("/webhooks/production", methods=["POST"])
@require_webhook_signature
def handle_webhook():
    """
    Обработчик входящих webhook событий.

    Заголовки запроса:
        - X-Webhook-Signature: t={timestamp},v1={signature}
        - X-Webhook-Event: Тип события
        - X-Webhook-Delivery-Id: ID доставки
        - X-Webhook-Timestamp: Unix timestamp

    Тело запроса (JSON):
        {
            "event": "batch_created",
            "data": {...},
            "timestamp": "2024-01-30T10:00:00Z"
        }
    """
    event_type = request.headers.get("X-Webhook-Event")
    delivery_id = request.headers.get("X-Webhook-Delivery-Id")
    data = request.get_json()

    logger.info(
        "Received webhook: event=%s, delivery_id=%s",
        event_type, delivery_id
    )

    # Роутинг по типу события
    handlers = {
        "batch_created": handle_batch_created,
        "batch_updated": handle_batch_updated,
        "batch_closed": handle_batch_closed,
        "product_aggregated": handle_product_aggregated,
        "report_generated": handle_report_generated,
        "import_completed": handle_import_completed,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data.get("data", {}))
        except Exception as e:
            logger.exception("Error handling webhook event: %s", event_type)
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        logger.warning("Unknown webhook event type: %s", event_type)

    return jsonify({"status": "ok", "received": event_type}), 200


# =============================================================================
# Event Handlers
# =============================================================================

def handle_batch_created(data: dict):
    """Обработка события создания партии."""
    logger.info(
        "Batch created: id=%s, number=%s, nomenclature=%s",
        data.get("id"),
        data.get("batch_number"),
        data.get("nomenclature")
    )
    # TODO: Ваша логика обработки


def handle_batch_updated(data: dict):
    """Обработка события обновления партии."""
    logger.info(
        "Batch updated: id=%s, number=%s, changes=%s",
        data.get("id"),
        data.get("batch_number"),
        data.get("changes")
    )
    # TODO: Ваша логика обработки


def handle_batch_closed(data: dict):
    """Обработка события закрытия партии."""
    logger.info(
        "Batch closed: id=%s, number=%s, stats=%s",
        data.get("id"),
        data.get("batch_number"),
        data.get("statistics")
    )
    # TODO: Ваша логика обработки


def handle_product_aggregated(data: dict):
    """Обработка события агрегации продукта."""
    logger.info(
        "Product aggregated: code=%s, batch_id=%s",
        data.get("unique_code"),
        data.get("batch_id")
    )
    # TODO: Ваша логика обработки


def handle_report_generated(data: dict):
    """Обработка события генерации отчёта."""
    logger.info(
        "Report generated: batch_id=%s, type=%s, url=%s",
        data.get("batch_id"),
        data.get("report_type"),
        data.get("file_url")
    )
    # TODO: Ваша логика обработки (например, скачать отчёт)


def handle_import_completed(data: dict):
    """Обработка события завершения импорта."""
    logger.info(
        "Import completed: total=%s, created=%s, skipped=%s, errors=%s",
        data.get("total_rows"),
        data.get("created"),
        data.get("skipped"),
        len(data.get("errors", []))
    )
    # TODO: Ваша логика обработки


# =============================================================================
# Health Check
# =============================================================================

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
