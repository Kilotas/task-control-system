from src.core.exceptions import AppException, NotFoundException, ServiceUnavailableException


class WebhookException(AppException):
    """Базовое исключение для webhook ошибок."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message=message, status_code=status_code)


class WebhookDeliveryNotFound(NotFoundException):
    """Delivery запись не найдена."""

    def __init__(self, delivery_id: int):
        super().__init__(resource="WebhookDelivery", identifier=delivery_id)
        self.delivery_id = delivery_id


class WebhookSubscriptionNotFound(NotFoundException):
    """Subscription не найдена."""

    def __init__(self, subscription_id: int):
        super().__init__(resource="WebhookSubscription", identifier=subscription_id)
        self.subscription_id = subscription_id


class WebhookSubscriptionInactive(WebhookException):
    """Subscription неактивна."""

    def __init__(self, subscription_id: int):
        super().__init__(
            message=f"WebhookSubscription is inactive: {subscription_id}",
            status_code=400
        )
        self.subscription_id = subscription_id


class WebhookDeliveryFailed(WebhookException):
    """Ошибка доставки webhook."""

    def __init__(self, delivery_id: int, reason: str):
        super().__init__(
            message=f"Webhook delivery failed: {reason}",
            status_code=502
        )
        self.delivery_id = delivery_id
        self.reason = reason


class WebhookTimeoutError(ServiceUnavailableException):
    """Таймаут при отправке webhook."""

    def __init__(self, delivery_id: int, url: str, timeout: float):
        super().__init__(message=f"Webhook timeout after {timeout}s to {url}")
        self.delivery_id = delivery_id
        self.url = url
        self.timeout = timeout


class WebhookConnectionError(ServiceUnavailableException):
    """Ошибка соединения при отправке webhook."""

    def __init__(self, delivery_id: int, url: str, error: str):
        super().__init__(message=f"Webhook connection error to {url}: {error}")
        self.delivery_id = delivery_id
        self.url = url
        self.error = error


class WebhookHttpError(WebhookException):
    """HTTP ошибка от получателя webhook."""

    def __init__(self, delivery_id: int, status_code: int, response_body: str | None = None):
        super().__init__(
            message=f"Webhook received HTTP {status_code}",
            status_code=502
        )
        self.delivery_id = delivery_id
        self.http_status_code = status_code
        self.response_body = response_body
