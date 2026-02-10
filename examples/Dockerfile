FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY webhook_receiver.py .

CMD ["python", "webhook_receiver.py"]
