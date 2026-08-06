import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class PointTransaction(Base):
    """Immutable, auditable point event.

    ``users.total_points`` remains a fast balance cache. This table is the
    source of truth for where that balance came from.
    """

    __tablename__ = "point_transactions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "module", "event_type", "source_id",
            name="uq_point_transaction_source",
        ),
        Index("ix_point_transactions_user_created", "user_id", "created_at"),
        Index("ix_point_transactions_module", "module"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    module = Column(String(30), nullable=False)
    event_type = Column(String(50), nullable=False)
    source_id = Column(String(100), nullable=False)
    points = Column(Integer, nullable=False)
    rule_version = Column(String(20), default="v1", nullable=False)
    description = Column(String(300), default="", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
