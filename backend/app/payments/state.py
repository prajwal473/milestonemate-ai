from enum import Enum


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CAPTURE_PENDING = "CAPTURE_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


# States from which no further transitions are allowed.
TERMINAL_STATUSES = {
    PaymentStatus.COMPLETED,
    PaymentStatus.FAILED,
    PaymentStatus.DENIED,
    PaymentStatus.CANCELLED,
}


# Allowed payment state transitions.
TRANSITIONS = {
    PaymentStatus.CREATED: {
        PaymentStatus.PENDING_APPROVAL,
        PaymentStatus.FAILED,
    },

    PaymentStatus.PENDING_APPROVAL: {
        PaymentStatus.APPROVED,
        PaymentStatus.FAILED,
        PaymentStatus.DENIED,
        PaymentStatus.CANCELLED,
    },

    PaymentStatus.APPROVED: {
        PaymentStatus.CAPTURE_PENDING,
        PaymentStatus.COMPLETED,
        PaymentStatus.FAILED,
        PaymentStatus.DENIED,
    },

    PaymentStatus.CAPTURE_PENDING: {
        PaymentStatus.COMPLETED,
        PaymentStatus.FAILED,
        PaymentStatus.DENIED,
    },

    PaymentStatus.COMPLETED: set(),
    PaymentStatus.FAILED: set(),
    PaymentStatus.DENIED: set(),
    PaymentStatus.CANCELLED: set(),
}


def can_transition(
    current: PaymentStatus | str,
    target: PaymentStatus | str,
) -> bool:
    """
    Check whether a payment can move from its current state
    to the requested target state.
    """

    try:
        current = PaymentStatus(current)
        target = PaymentStatus(target)
    except ValueError:
        return False

    return target in TRANSITIONS.get(current, set())


def validate_transition(
    current: PaymentStatus | str,
    target: PaymentStatus | str,
) -> None:
    """
    Validate a payment state transition.

    Raises ValueError if the transition is not allowed.
    """

    if not can_transition(current, target):
        raise ValueError(
            f"Invalid payment transition: {current} -> {target}"
        )