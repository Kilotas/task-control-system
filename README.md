# Production Control API

Система контроля производственных партий с поддержкой агрегации продуктов, аналитики, вебхуков и асинхронной обработки задач.

## Технологии

- **FastAPI** - веб-фреймворк
- **PostgreSQL** - база данных
- **Redis** - кэширование и брокер результатов Celery
- **RabbitMQ** - брокер сообщений Celery
- **Celery** - асинхронные задачи
- **MinIO** - S3-совместимое хранилище файлов
- **Flower** - мониторинг Celery

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd task-control-system

# Создать .env файл
cp .env.example .env
```

### 2. Запуск через Docker

```bash
# Запустить все сервисы
docker-compose up -d

# Применить миграции
docker-compose run --rm migrate
```

### 3. Доступ к сервисам

| Сервис | URL |
|--------|-----|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Flower (Celery) | http://localhost:5555 |
| MinIO Console | http://localhost:9001 |
| RabbitMQ | http://localhost:15672 |

## API Endpoints

### Партии (Batches)

```
POST   /api/v1/batches              - Создать партии
GET    /api/v1/batches              - Список партий
GET    /api/v1/batches/{id}         - Получить партию
PATCH  /api/v1/batches/{id}         - Обновить партию
POST   /api/v1/batches/{id}/aggregate      - Агрегация продуктов
POST   /api/v1/batches/{id}/aggregate-async - Асинхронная агрегация
POST   /api/v1/batches/{id}/reports - Генерация отчёта
POST   /api/v1/batches/import       - Импорт из Excel
POST   /api/v1/batches/export       - Экспорт в файл
```

### Аналитика (Analytics)

```
GET    /api/v1/analytics/dashboard                    - Статистика дашборда
GET    /api/v1/analytics/batches/{id}/statistics      - Статистика партии
POST   /api/v1/analytics/compare-batches              - Сравнение партий
```

### Вебхуки (Webhooks)

```
POST   /api/v1/webhooks                      - Создать подписку
GET    /api/v1/webhooks                      - Список подписок
PATCH  /api/v1/webhooks/{id}                 - Обновить подписку
DELETE /api/v1/webhooks/{id}                 - Удалить подписку
GET    /api/v1/webhooks/{id}/deliveries      - История доставок
GET    /api/v1/webhooks/circuit-breaker/status - Статус Circuit Breaker
```

### Продукты (Products)

```
POST   /api/v1/products             - Создать продукт
```

### Задачи (Tasks)

```
GET    /api/v1/tasks/{task_id}      - Статус Celery задачи
```

## Архитектура

```
src/
├── api/v1/
│   ├── routers/          # FastAPI роутеры
│   └── schemas/          # Pydantic схемы
├── application/
│   └── uow/              # Unit of Work паттерн
├── core/
│   ├── config.py         # Настройки
│   ├── dependencies.py   # FastAPI зависимости
│   ├── rate_limiter.py   # Rate Limiting (slowapi)
│   └── circuit_breaker.py # Circuit Breaker паттерн
├── data/
│   ├── models/           # SQLAlchemy модели
│   └── repositories/     # Репозитории
├── domain/
│   ├── services/         # Бизнес-логика
│   ├── mappers/          # Маппинг DTO
│   └── exceptions/       # Кастомные исключения
├── storage/
│   └── minio_service.py  # MinIO клиент
└── tasks/                # Celery задачи
```

## Паттерны

### Circuit Breaker

Защита от каскадных сбоев при отправке вебхуков:

```
CLOSED (норма) → 5 ошибок → OPEN (блок) → 60 сек → HALF_OPEN (проба) → 2 успеха → CLOSED
```

### Rate Limiting

- Глобальный лимит: 100 запросов/минуту
- Создание партий: 30/минуту
- Импорт: 5/минуту
- Экспорт: 10/минуту

### Кэширование

- Dashboard статистика: TTL 5 минут
- Статистика партии: TTL 5 минут
- Автоматическая инвалидация при изменении данных

## Тестирование

```bash
# Запуск тестов в Docker
docker-compose --profile test run --rm tests

# Локальный запуск
pip install pytest pytest-asyncio
pytest -v
```

## Переменные окружения

```env
# База данных
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/production_control

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123456

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

## Вебхуки

### События

- `batch.created` - создана партия
- `batch.closed` - партия закрыта
- `product.aggregated` - продукт агрегирован

### Формат payload

```json
{
  "event": "batch.created",
  "data": {
    "batch_id": 1,
    "batch_number": 1001
  },
  "timestamp": "2026-02-05T10:00:00Z"
}
```

### Заголовки

```
X-Webhook-Signature: t=1234567890,v1=<hmac-sha256>
X-Webhook-Event: batch.created
X-Webhook-Delivery-Id: 123
X-Webhook-Timestamp: 1234567890
```

### Верификация подписи (Python)

```python
import hmac
import hashlib

def verify_signature(payload: str, signature: str, secret: str) -> bool:
    parts = dict(p.split("=") for p in signature.split(","))
    timestamp = parts["t"]
    expected = parts["v1"]

    signed_payload = f"{timestamp}.{payload}"
    computed = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, expected)
```

## Разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск локально
uvicorn src.main:app --reload

# Celery worker
celery -A src.celery_app.celery_app worker --loglevel=info

# Celery beat (планировщик)
celery -A src.celery_app.celery_app beat --loglevel=info

# Flower (мониторинг)
celery -A src.celery_app.celery_app flower --port=5555
```

## Лицензия

MIT
