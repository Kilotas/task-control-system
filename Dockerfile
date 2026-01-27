FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.128.0 \
    uvicorn[standard]==0.40.0 \
    pydantic-settings==2.12.0 \
    sqlalchemy==2.0.0 \
    asyncpg==0.31.0 \
    alembic==1.18.0 \
    celery==5.3.0 \
    redis==7.1.0 \
    boto3==1.42.26 \
    httpx==0.28.1 \
    kombu==5.3.0 \
    amqp==5.2.0 \
    psycopg2-binary==2.9.9

COPY . .

ENV PYTHONPATH=/app

CMD ["celery", "-A", "src.celery_app.celery_app", "worker", "--loglevel=info"]
