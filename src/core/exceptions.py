from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """
    Базовое исключение для всех ошибок приложения.
    Все кастомные исключения должны наследоваться от этого класса.
    """

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def __str__(self):
        return f"[{self.status_code}] {self.message}"


class NotFoundException(AppException):
    """
    Базовое исключение для случаев "не найдено".
    Автоматически устанавливает status_code=404.
    """

    def __init__(self, resource: str, identifier):
        super().__init__(message=f"{resource} not found: {identifier}", status_code=404)
        self.resource = resource
        self.identifier = identifier


class ValidationException(AppException):
    """
    Базовое исключение для ошибок валидации.
    Автоматически устанавливает status_code=400.
    """

    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)


class ConflictException(AppException):
    """
    Базовое исключение для конфликтующих данных.
    Автоматически устанавливает status_code=409.
    """

    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class ServiceUnavailableException(AppException):
    """
    Базовое исключение для недоступных внешних сервисов.
    Автоматически устанавливает status_code=503.
    """

    def __init__(self, message: str):
        super().__init__(message=message, status_code=503)


class GatewayTimeoutException(AppException):
    """
    Базовое исключение для таймаутов внешних сервисов.
    Автоматически устанавливает status_code=504.
    """

    def __init__(self, message: str):
        super().__init__(message=message, status_code=504)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Зарегистрировать обработчики кастомных исключений приложения.
    Любое AppException (и все его наследники) будет превращаться
    в JSON-ответ вида:
    {
        "detail": "...",
    }
    с нужным статус-кодом.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )