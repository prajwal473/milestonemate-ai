from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now,
        onupdate=utc_now, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    client_projects: Mapped[list["Project"]] = relationship(
        foreign_keys="Project.client_id", back_populates="client"
    )
    freelancer_projects: Mapped[list["Project"]] = relationship(
        foreign_keys="Project.freelancer_id", back_populates="freelancer"
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="draft")

    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    freelancer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    client: Mapped["User"] = relationship(
        foreign_keys=[client_id], back_populates="client_projects"
    )
    freelancer: Mapped["User | None"] = relationship(
        foreign_keys=[freelancer_id], back_populates="freelancer_projects"
    )
    agreements: Mapped[list["Agreement"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Agreement(TimestampMixin, Base):
    __tablename__ = "agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    client_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    freelancer_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    project: Mapped["Project"] = relationship(back_populates="agreements")
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="agreement"
    )


class Milestone(TimestampMixin, Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False
    )
    agreement_id: Mapped[int | None] = mapped_column(
        ForeignKey("agreements.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acceptance_criteria: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")

    project: Mapped["Project"] = relationship(back_populates="milestones")
    agreement: Mapped["Agreement | None"] = relationship(
        back_populates="milestones"
    )
    deliverables: Mapped[list["Deliverable"]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="milestone"
    )


class Deliverable(TimestampMixin, Base):
    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    milestone_id: Mapped[int] = mapped_column(
        ForeignKey("milestones.id"), nullable=False
    )
    submitted_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    file_urls: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="submitted")

    milestone: Mapped["Milestone"] = relationship(back_populates="deliverables")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan"
    )


class Evaluation(TimestampMixin, Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverables.id"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(100))
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    findings: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    human_decision: Mapped[str | None] = mapped_column(String(50))

    deliverable: Mapped["Deliverable"] = relationship(
        back_populates="evaluations"
    )


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    milestone_id: Mapped[int] = mapped_column(
        ForeignKey("milestones.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    paypal_order_id: Mapped[str | None] = mapped_column(
        String(100), unique=True
    )
    paypal_capture_id: Mapped[str | None] = mapped_column(
        String(100), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending")

    milestone: Mapped["Milestone"] = relationship(back_populates="payments")
