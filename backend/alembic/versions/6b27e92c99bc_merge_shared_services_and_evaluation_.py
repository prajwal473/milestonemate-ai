"""merge shared services and evaluation migrations

Revision ID: 6b27e92c99bc
Revises: 478209cd1f31, feb92a81ade5
Create Date: 2026-11-11 13:05:26.341336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b27e92c99bc'
down_revision: Union[str, Sequence[str], None] = ('478209cd1f31', 'feb92a81ade5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
