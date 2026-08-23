"""initial schema

Revision ID: 8819a382188d
Revises:
Create Date: 2026-08-23 02:50:02.500842

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8819a382188d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("service", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_logs_timestamp",
        "logs",
        ["timestamp"],
        unique=False,
    )

    op.create_index(
        "ix_logs_level",
        "logs",
        ["level"],
        unique=False,
    )

    op.create_index(
        "ix_logs_service",
        "logs",
        ["service"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_logs_service", table_name="logs")
    op.drop_index("ix_logs_level", table_name="logs")
    op.drop_index("ix_logs_timestamp", table_name="logs")
    op.drop_table("logs")
