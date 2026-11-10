class PaymentError(Exception):
    """Base exception for payment-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class PaymentNotFoundError(PaymentError):
    """Raised when a requested payment does not exist."""


class InvalidPaymentStateError(PaymentError):
    """Raised when an invalid payment state transition is attempted."""


class PayPalError(PaymentError):
    """Raised when PayPal API operations fail."""


class AmountMismatchError(PaymentError):
    """Raised when payment amount differs from expected amount."""


class WebhookVerificationError(PaymentError):
    """Raised when PayPal webhook signature verification fails."""


class IdempotencyConflictError(PaymentError):
    """Raised when an idempotency key is reused with different data."""


class PaymentAuthorizationError(PaymentError):
    """Raised when a user is not authorized to perform a payment action."""