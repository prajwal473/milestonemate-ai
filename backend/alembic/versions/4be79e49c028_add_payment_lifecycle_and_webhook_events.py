
"""add payment lifecycle and webhook events

Revision ID: 4be79e49c028
Revises: 24fb06e8eeb9
Create Date: 2026-11-09 14:54:26.352009
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4be79e49c028"
down_revision: Union[str, Sequence[str], None] = "24fb06e8eeb9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE_STATUSES = (
    "'CREATED','PENDING_APPROVAL','APPROVED','CAPTURE_PENDING'"
)

VALID_STATUSES = (
    "'CREATED','PENDING_APPROVAL','APPROVED',"
    "'CAPTURE_PENDING','COMPLETED','FAILED','DENIED','CANCELLED'"
)


def upgrade() -> None:
    # Create webhook event storage.
    op.create_table(
        "paypal_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paypal_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("processing_status", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("transmission_id", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "processing_status IN ('RECEIVED','PROCESSED','IGNORED','FAILED')",
            name=op.f("ck_paypal_webhook_events_processing"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('SUCCESS','FAILURE','ERROR')",
            name=op.f("ck_paypal_webhook_events_verification"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paypal_webhook_events")),
        sa.UniqueConstraint(
            "paypal_event_id",
            name=op.f("uq_paypal_webhook_events_paypal_event_id"),
        ),
    )

    # Create payment audit events.
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("paypal_ref", sa.String(255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('API','WEBHOOK','SYSTEM','USER')",
            name=op.f("ck_payment_events_source"),
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_payment_events_payment_id_payments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_events")),
    )

    op.create_index(
        "payment_events_payment_idx",
        "payment_events",
        ["payment_id", "created_at"],
    )

    # Add new payment fields as nullable first so existing rows remain valid.
    op.add_column("payments", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("payer_id", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("provider", sa.String(20), nullable=True))
    op.add_column("payments", sa.Column("payee_mode", sa.String(30), nullable=True))
    op.add_column("payments", sa.Column("payee_email", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("idempotency_key", sa.String(100), nullable=True))
    op.add_column("payments", sa.Column("paypal_order_status", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("paypal_capture_status", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("approve_url", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("failure_code", sa.String(100), nullable=True))
    op.add_column("payments", sa.Column("failure_message", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill ownership and project information from existing relationships.
    op.execute(
        """
        UPDATE payments AS p
        SET
            project_id = m.project_id,
            payer_id = pr.client_id
        FROM milestones AS m
        JOIN projects AS pr ON pr.id = m.project_id
        WHERE p.milestone_id = m.id
        """
    )

    # Set defaults for legacy payment rows.
    op.execute(
        """
        UPDATE payments
        SET
            provider = 'PAYPAL',
            payee_mode = 'demo_merchant',
            idempotency_key = 'legacy-payment-' || id::text
        """
    )

    # Fail clearly if ownership backfill could not resolve a relationship.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM payments
                WHERE project_id IS NULL OR payer_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Payment migration aborted: could not resolve project_id or payer_id for every payment';
            END IF;
        END $$;
        """
    )

    # Validate legacy statuses before enforcing the new status constraint.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM payments
                WHERE status NOT IN ({VALID_STATUSES})
            ) THEN
                RAISE EXCEPTION
                    'Payment migration aborted: unsupported legacy payment status found';
            END IF;
        END $$;
        """
    )

    # Enforce NOT NULL after backfilling.
    op.alter_column("payments", "project_id", nullable=False)
    op.alter_column("payments", "payer_id", nullable=False)
    op.alter_column("payments", "provider", nullable=False)
    op.alter_column("payments", "payee_mode", nullable=False)
    op.alter_column("payments", "idempotency_key", nullable=False)

    # Foreign keys for new ownership fields.
    op.create_foreign_key(
        op.f("fk_payments_project_id_projects"),
        "payments",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_payments_payer_id_users"),
        "payments",
        "users",
        ["payer_id"],
        ["id"],
    )

    # Constraints matching the SQLAlchemy Payment model.
    op.create_check_constraint(
        op.f("ck_payments_amount_positive"),
        "payments",
        "amount > 0",
    )
    op.create_check_constraint(
        op.f("ck_payments_currency"),
        "payments",
        "currency = 'USD'",
    )
    op.create_check_constraint(
        op.f("ck_payments_status"),
        "payments",
        f"status IN ({VALID_STATUSES})",
    )
    op.create_check_constraint(
        op.f("ck_payments_provider"),
        "payments",
        "provider IN ('PAYPAL','MOCK')",
    )
    op.create_check_constraint(
        op.f("ck_payments_payee_mode"),
        "payments",
        "payee_mode IN ('demo_merchant','direct_payee')",
    )

    # One live payment per milestone. Terminal states are excluded.
    op.create_index(
        "payments_one_live_per_milestone_uq",
        "payments",
        ["milestone_id"],
        unique=True,
        postgresql_where=sa.text(f"status IN ({ACTIVE_STATUSES})"),
    )

    op.create_index(
        "payments_project_idx",
        "payments",
        ["project_id", sa.literal_column("created_at DESC")],
    )

    # Idempotency is scoped to provider and payer.
    op.create_unique_constraint(
        "uq_payments_provider_payer_idempotency_key",
        "payments",
        ["provider", "payer_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payments_provider_payer_idempotency_key",
        "payments",
        type_="unique",
    )

    op.drop_index("payments_project_idx", table_name="payments")
    op.drop_index("payments_one_live_per_milestone_uq", table_name="payments")

    op.drop_constraint(op.f("ck_payments_payee_mode"), "payments", type_="check")
    op.drop_constraint(op.f("ck_payments_provider"), "payments", type_="check")
    op.drop_constraint(op.f("ck_payments_status"), "payments", type_="check")
    op.drop_constraint(op.f("ck_payments_currency"), "payments", type_="check")
    op.drop_constraint(op.f("ck_payments_amount_positive"), "payments", type_="check")

    op.drop_constraint(
        op.f("fk_payments_payer_id_users"),
        "payments",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_payments_project_id_projects"),
        "payments",
        type_="foreignkey",
    )

    op.drop_column("payments", "captured_at")
    op.drop_column("payments", "approved_at")
    op.drop_column("payments", "failure_message")
    op.drop_column("payments", "failure_code")
    op.drop_column("payments", "approve_url")
    op.drop_column("payments", "paypal_capture_status")
    op.drop_column("payments", "paypal_order_status")
    op.drop_column("payments", "idempotency_key")
    op.drop_column("payments", "payee_email")
    op.drop_column("payments", "payee_mode")
    op.drop_column("payments", "provider")
    op.drop_column("payments", "payer_id")
    op.drop_column("payments", "project_id")

    op.drop_index("payment_events_payment_idx", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_table("paypal_webhook_events")
