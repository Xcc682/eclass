"""Add auditable point transactions and backfill the current balance."""

import json
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "0010_point_ledger"
down_revision = "0009_training_flow_v2"
branch_labels = None
depends_on = None


def _insert_event(bind, *, user_id, module, event_type, source_id, points, description, created_at, metadata=None):
    bind.execute(sa.text(
        "INSERT INTO point_transactions "
        "(id, user_id, module, event_type, source_id, points, rule_version, description, metadata_json, created_at) "
        "VALUES (:id, :user_id, :module, :event_type, :source_id, :points, :rule_version, :description, :metadata_json, :created_at)"
    ), {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "module": module,
        "event_type": event_type,
        "source_id": str(source_id),
        "points": int(points),
        "rule_version": "legacy-backfill",
        "description": description,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        "created_at": created_at or datetime.utcnow(),
    })


def upgrade():
    op.create_table(
        "point_transactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("module", sa.String(30), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(20), server_default="v1", nullable=False),
        sa.Column("description", sa.String(300), server_default="", nullable=False),
        sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "module", "event_type", "source_id", name="uq_point_transaction_source"),
    )
    op.create_index("ix_point_transactions_user_created", "point_transactions", ["user_id", "created_at"])
    op.create_index("ix_point_transactions_module", "point_transactions", ["module"])

    bind = op.get_bind()
    traced: dict[str, int] = {}

    interviews = bind.execute(sa.text(
        "SELECT r.id, r.user_id, r.overall_score, r.completed_at "
        "FROM interview_practice_records r "
        "WHERE r.status = 'completed' AND r.flow_version = 2 AND r.is_legacy IS FALSE "
        "AND r.total_rounds = 6 AND r.report_json IS NOT NULL "
        "AND EXISTS (SELECT 1 FROM generated_reports g WHERE g.report_type = 'interview' AND g.source_record_id = r.id)"
    )).mappings()
    for row in interviews:
        points = max(int(row["overall_score"] or 0) // 10, 1)
        _insert_event(bind, user_id=row["user_id"], module="interview", event_type="practice_completed",
                      source_id=row["id"], points=points, description="完成入党谈话训练",
                      created_at=row["completed_at"], metadata={"score": row["overall_score"]})
        traced[row["user_id"]] = traced.get(row["user_id"], 0) + points

    debates = bind.execute(sa.text(
        "SELECT r.id, r.user_id, r.overall_score, r.completed_at "
        "FROM debate_practice_records r "
        "WHERE r.status = 'completed' AND r.flow_version = 2 AND r.is_legacy IS FALSE "
        "AND r.feedback_json IS NOT NULL "
        "AND ((r.mode = 'quick' AND r.total_rounds = 4) OR (r.mode = 'full' AND r.total_rounds = 6)) "
        "AND EXISTS (SELECT 1 FROM generated_reports g WHERE g.report_type = 'debate' AND g.source_record_id = r.id)"
    )).mappings()
    for row in debates:
        points = max(int(row["overall_score"] or 0) // 10, 1)
        _insert_event(bind, user_id=row["user_id"], module="debate", event_type="practice_completed",
                      source_id=row["id"], points=points, description="完成思政辩论训练",
                      created_at=row["completed_at"], metadata={"score": row["overall_score"]})
        traced[row["user_id"]] = traced.get(row["user_id"], 0) + points

    histories = bind.execute(sa.text(
        "SELECT id, user_id, scenario_id, completed_at FROM history_learning_records WHERE completed IS TRUE "
        "ORDER BY completed_at, id"
    )).mappings()
    seen_history = set()
    for row in histories:
        source_key = (row["user_id"], row["scenario_id"])
        if source_key in seen_history:
            continue
        seen_history.add(source_key)
        _insert_event(bind, user_id=row["user_id"], module="history", event_type="scenario_completed",
                      source_id=row["scenario_id"], points=2, description="完成党史情景学习",
                      created_at=row["completed_at"], metadata={"record_id": row["id"]})
        traced[row["user_id"]] = traced.get(row["user_id"], 0) + 2

    tours = bind.execute(sa.text(
        "SELECT id, user_id, site_id, completed_at FROM tour_records WHERE completed IS TRUE "
        "ORDER BY completed_at, id"
    )).mappings()
    seen_tours = set()
    for row in tours:
        source_key = (row["user_id"], row["site_id"])
        if source_key in seen_tours:
            continue
        seen_tours.add(source_key)
        _insert_event(bind, user_id=row["user_id"], module="tour", event_type="site_completed",
                      source_id=row["site_id"], points=3, description="完成红色研学",
                      created_at=row["completed_at"], metadata={"record_id": row["id"]})
        traced[row["user_id"]] = traced.get(row["user_id"], 0) + 3

    users = bind.execute(sa.text("SELECT id, total_points, created_at FROM users")).mappings()
    for row in users:
        legacy_balance = int(row["total_points"] or 0) - traced.get(row["id"], 0)
        if legacy_balance:
            _insert_event(
                bind, user_id=row["id"], module="system", event_type="legacy_balance",
                source_id=row["id"], points=legacy_balance, description="迁移前历史积分余额",
                created_at=row["created_at"], metadata={"reason": "无法从现行有效记录还原，原值予以保留"},
            )


def downgrade():
    op.drop_index("ix_point_transactions_module", table_name="point_transactions")
    op.drop_index("ix_point_transactions_user_created", table_name="point_transactions")
    op.drop_table("point_transactions")
