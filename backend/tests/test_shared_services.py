from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    AuditLog,
    Milestone,
    Notification,
    Project,
    User,
)
from app.services.audit import record
from app.services.milestones import get_for_payment, mark_paid
from app.services.notifications import notify


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_project_with_users(db):
    client = User(
        name="Test Client",
        email="client@test.com",
        password_hash="test_hash",
        role="client",
    )

    freelancer = User(
        name="Test Freelancer",
        email="freelancer@test.com",
        password_hash="test_hash",
        role="freelancer",
    )

    db.add_all([client, freelancer])
    db.flush()

    project = Project(
        title="Test Project",
        description="Project for shared service tests",
        budget=Decimal("1000.00"),
        currency="USD",
        status="active",
        client_id=client.id,
        freelancer_id=freelancer.id,
    )

    db.add(project)
    db.flush()

    return client, freelancer, project


def create_milestone(db, project, title="Test Milestone", status="approved"):
    milestone = Milestone(
        project_id=project.id,
        title=title,
        description="Test milestone description",
        amount=Decimal("500.00"),
        acceptance_criteria=["Requirement completed"],
        status=status,
    )

    db.add(milestone)
    db.flush()

    return milestone


def test_get_for_payment_returns_approved_milestone(db):
    client, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project)

    result = get_for_payment(db, milestone.id, client.id)

    assert result.id == milestone.id
    assert result.status == "approved"
    assert result.project.client_id == client.id


def test_get_for_payment_rejects_non_client(db):
    _, freelancer, project = create_project_with_users(db)
    milestone = create_milestone(db, project)

    with pytest.raises(PermissionError):
        get_for_payment(db, milestone.id, freelancer.id)


def test_get_for_payment_rejects_missing_milestone(db):
    client, _, _ = create_project_with_users(db)

    with pytest.raises(ValueError, match="Milestone not found"):
        get_for_payment(db, 99999, client.id)


def test_get_for_payment_rejects_unapproved_milestone(db):
    client, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project, status="pending")

    with pytest.raises(ValueError, match="approved"):
        get_for_payment(db, milestone.id, client.id)


def test_mark_paid_updates_milestone(db):
    _, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project)

    result = mark_paid(db, milestone.id, payment_id=1)

    assert result.status == "paid"


def test_project_completes_only_after_all_milestones_are_paid(db):
    _, _, project = create_project_with_users(db)

    first = create_milestone(db, project, title="First")
    second = create_milestone(db, project, title="Second")

    mark_paid(db, first.id, payment_id=1)
    db.flush()

    assert project.status == "active"
    assert second.status == "approved"

    mark_paid(db, second.id, payment_id=2)
    db.flush()

    assert project.status == "completed"


def test_mark_paid_rejects_invalid_payment_id(db):
    _, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project)

    with pytest.raises(ValueError, match="positive integer"):
        mark_paid(db, milestone.id, payment_id=0)


def test_mark_paid_rejects_unapproved_milestone(db):
    _, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project, status="pending")

    with pytest.raises(ValueError, match="approved"):
        mark_paid(db, milestone.id, payment_id=1)


def test_audit_record_creates_log(db):
    client, _, _ = create_project_with_users(db)

    entry = record(
        db,
        actor_id=client.id,
        action="milestone.paid",
        entity_type="milestone",
        entity_id=1,
        details={"payment_id": 10},
    )

    assert entry.id is not None
    assert entry.actor_id == client.id
    assert entry.action == "milestone.paid"
    assert entry.details == {"payment_id": 10}
    assert db.query(AuditLog).count() == 1


def test_audit_record_supports_system_actor(db):
    entry = record(
        db,
        actor_id=None,
        action="payment.webhook_received",
        entity_type="payment",
        entity_id=10,
    )

    assert entry.actor_id is None
    assert entry.details == {}


def test_audit_record_rejects_invalid_entity_id(db):
    with pytest.raises(ValueError, match="positive integer"):
        record(
            db,
            actor_id=None,
            action="test",
            entity_type="test",
            entity_id=0,
        )


def test_notification_creates_persisted_notification(db):
    client, _, _ = create_project_with_users(db)

    notification = notify(
        db,
        user_id=client.id,
        event_type="milestone.paid",
        payload={
            "project_id": 1,
            "milestone_id": 2,
            "payment_id": 3,
        },
    )

    assert notification.id is not None
    assert notification.user_id == client.id
    assert notification.event_type == "milestone.paid"
    assert notification.payload["payment_id"] == 3
    assert notification.read_at is None
    assert db.query(Notification).count() == 1


def test_notification_rejects_invalid_user_id(db):
    with pytest.raises(ValueError, match="positive integer"):
        notify(
            db,
            user_id=0,
            event_type="test",
            payload={},
        )


def test_shared_services_do_not_commit_the_transaction(db):
    client, _, project = create_project_with_users(db)
    milestone = create_milestone(db, project)

    # Persist the initial test data.
    db.commit()

    mark_paid(db, milestone.id, payment_id=1)

    record(
        db,
        actor_id=client.id,
        action="test",
        entity_type="milestone",
        entity_id=milestone.id,
    )

    notify(
        db,
        user_id=client.id,
        event_type="test",
        payload={},
    )

    # Roll back only the service operations.
    db.rollback()
    db.expire_all()

    assert db.query(Milestone).filter_by(id=milestone.id).one().status == "approved"
    assert db.query(Project).filter_by(id=project.id).one().status == "active"
    assert db.query(AuditLog).count() == 0
    assert db.query(Notification).count() == 0