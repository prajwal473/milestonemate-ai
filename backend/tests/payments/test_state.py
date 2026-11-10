import pytest

from app.payments.state import PaymentStatus, can_transition, validate_transition


@pytest.mark.parametrize("current,target", [
    (PaymentStatus.CREATED, PaymentStatus.PENDING_APPROVAL),
    (PaymentStatus.CREATED, PaymentStatus.FAILED),
    (PaymentStatus.PENDING_APPROVAL, PaymentStatus.APPROVED),
    (PaymentStatus.PENDING_APPROVAL, PaymentStatus.CANCELLED),
    (PaymentStatus.APPROVED, PaymentStatus.CAPTURE_PENDING),
    (PaymentStatus.APPROVED, PaymentStatus.COMPLETED),
    (PaymentStatus.CAPTURE_PENDING, PaymentStatus.COMPLETED),
    (PaymentStatus.CAPTURE_PENDING, PaymentStatus.DENIED),
])
def test_allowed_state_transitions(current, target):
    assert can_transition(current, target)
    validate_transition(current, target)


@pytest.mark.parametrize("current,target", [
    (PaymentStatus.COMPLETED, PaymentStatus.FAILED),
    (PaymentStatus.CANCELLED, PaymentStatus.APPROVED),
    (PaymentStatus.DENIED, PaymentStatus.COMPLETED),
    (PaymentStatus.PENDING_APPROVAL, PaymentStatus.COMPLETED),
    (PaymentStatus.CREATED, PaymentStatus.APPROVED),
])
def test_forbidden_state_transitions(current, target):
    assert not can_transition(current, target)
    with pytest.raises(ValueError):
        validate_transition(current, target)


def test_unknown_state_is_not_allowed():
    assert not can_transition("UNKNOWN", PaymentStatus.COMPLETED)
