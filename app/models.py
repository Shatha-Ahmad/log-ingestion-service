from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    service: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        Index(
            "ix_logs_attributes",
            "attributes",
            postgresql_using="gin",
        ),
    )