"""add attributes gin index

Revision ID: e2d621b301f0
Revises: 8819a382188d
Create Date: 2026-08-23 02:58:47.232933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2d621b301f0'
down_revision: Union[str, Sequence[str], None] = '8819a382188d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_logs_attributes",
        "logs",
        ["attributes"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_logs_attributes",
        table_name="logs",
    )
