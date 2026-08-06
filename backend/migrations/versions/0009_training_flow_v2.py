"""Version interview and debate flows and add idempotent submissions."""

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "0009_training_flow_v2"
down_revision = "0008_training_data_repair"
branch_labels = None
depends_on = None


def _message_counts(bind, table: str) -> dict[str, int]:
    rows = bind.execute(sa.text(
        f"SELECT record_id, COUNT(*) AS amount FROM {table} "
        "WHERE role = 'user' GROUP BY record_id"
    )).mappings()
    return {row["record_id"]: int(row["amount"] or 0) for row in rows}


def _normalize_user_rounds(bind, table: str) -> None:
    rows = bind.execute(sa.text(
        f"SELECT id, record_id FROM {table} WHERE role = 'user' "
        "ORDER BY record_id, created_at, id"
    )).mappings()
    counters: dict[str, int] = defaultdict(int)
    for row in rows:
        counters[row["record_id"]] += 1
        bind.execute(
            sa.text(f"UPDATE {table} SET round_number = :round_number WHERE id = :id"),
            {"round_number": counters[row["record_id"]], "id": row["id"]},
        )


def upgrade():
    with op.batch_alter_table("interview_practice_records") as batch:
        batch.add_column(sa.Column("requested_scenario_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("flow_version", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("is_legacy", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch.add_column(sa.Column("active_key", sa.String(500), nullable=True))
        batch.add_column(sa.Column("report_status", sa.String(20), server_default="idle", nullable=False))
        batch.add_column(sa.Column("report_started_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_interview_requested_scenario", "interview_scenarios", ["requested_scenario_id"], ["id"]
        )
        batch.create_unique_constraint("uq_interview_active_key", ["active_key"])

    with op.batch_alter_table("interview_messages") as batch:
        batch.add_column(sa.Column("submission_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("delivery_status", sa.String(20), server_default="sent", nullable=False))
        batch.create_unique_constraint(
            "uq_interview_submission_role", ["record_id", "role", "submission_id"]
        )

    with op.batch_alter_table("debate_practice_records") as batch:
        batch.add_column(sa.Column("flow_version", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("is_legacy", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch.add_column(sa.Column("active_key", sa.String(500), nullable=True))
        batch.add_column(sa.Column("report_status", sa.String(20), server_default="idle", nullable=False))
        batch.add_column(sa.Column("report_started_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_debate_active_key", ["active_key"])

    with op.batch_alter_table("debate_messages") as batch:
        batch.add_column(sa.Column("submission_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("delivery_status", sa.String(20), server_default="sent", nullable=False))
        batch.create_unique_constraint(
            "uq_debate_submission_role", ["record_id", "role", "submission_id"]
        )

    bind = op.get_bind()
    interview_counts = _message_counts(bind, "interview_messages")
    debate_counts = _message_counts(bind, "debate_messages")
    _normalize_user_rounds(bind, "interview_messages")
    _normalize_user_rounds(bind, "debate_messages")

    interview_rows = bind.execute(sa.text(
        "SELECT id, user_id, scenario_id, status, report_json, current_step "
        "FROM interview_practice_records ORDER BY started_at DESC, id DESC"
    )).mappings().all()
    seen_interviews: set[str] = set()
    for row in interview_rows:
        count = interview_counts.get(row["id"], 0)
        terminal_valid = row["status"] == "completed" and count == 6 and bool(row["report_json"])
        active_valid = row["status"] in {"in_progress", "awaiting_report"} and count <= 6
        valid = terminal_valid or active_valid
        status = row["status"]
        active_key = None
        if active_valid:
            candidate = f"{row['user_id']}:interview:{row['scenario_id']}"
            if candidate in seen_interviews:
                valid = False
                status = "abandoned"
            else:
                seen_interviews.add(candidate)
                active_key = candidate
        bind.execute(sa.text(
            "UPDATE interview_practice_records SET requested_scenario_id=:scenario_id, "
            "total_rounds=:count, current_step=:step, flow_version=:version, is_legacy=:legacy, "
            "status=:status, active_key=:active_key, report_status=:report_status WHERE id=:id"
        ), {
            "scenario_id": row["scenario_id"], "count": count, "step": min(count, 6),
            "version": 2 if valid else 1, "legacy": not valid, "status": status,
            "active_key": active_key if valid else None,
            "report_status": "completed" if terminal_valid else "idle", "id": row["id"],
        })

    debate_rows = bind.execute(sa.text(
        "SELECT id, user_id, topic_id, stance, mode, status, feedback_json "
        "FROM debate_practice_records ORDER BY started_at DESC, id DESC"
    )).mappings().all()
    seen_debates: set[str] = set()
    for row in debate_rows:
        count = debate_counts.get(row["id"], 0)
        expected = 6 if row["mode"] == "full" else 4
        terminal_valid = row["status"] == "completed" and count == expected and bool(row["feedback_json"])
        awaiting_valid = row["status"] == "awaiting_feedback" and count == expected
        active_valid = row["status"] == "in_progress" and count < expected
        valid = terminal_valid or awaiting_valid or active_valid
        status = row["status"]
        active_key = None
        if active_valid or awaiting_valid:
            candidate = f"{row['user_id']}:debate:{row['topic_id']}:{row['stance']}"
            if candidate in seen_debates:
                valid = False
                status = "abandoned"
            else:
                seen_debates.add(candidate)
                active_key = candidate
        bind.execute(sa.text(
            "UPDATE debate_practice_records SET total_rounds=:count, current_step=:step, "
            "flow_version=:version, is_legacy=:legacy, status=:status, active_key=:active_key, "
            "report_status=:report_status WHERE id=:id"
        ), {
            "count": count, "step": min(count, expected), "version": 2 if valid else 1,
            "legacy": not valid, "status": status, "active_key": active_key if valid else None,
            "report_status": "completed" if terminal_valid else "idle", "id": row["id"],
        })

    op.create_index(
        "uq_interview_user_round", "interview_messages", ["record_id", "round_number"],
        unique=True, sqlite_where=sa.text("role = 'user'"), postgresql_where=sa.text("role = 'user'"),
    )
    op.create_index(
        "uq_debate_user_round", "debate_messages", ["record_id", "round_number"],
        unique=True, sqlite_where=sa.text("role = 'user'"), postgresql_where=sa.text("role = 'user'"),
    )


def downgrade():
    op.drop_index("uq_debate_user_round", table_name="debate_messages")
    op.drop_index("uq_interview_user_round", table_name="interview_messages")
    with op.batch_alter_table("debate_messages") as batch:
        batch.drop_constraint("uq_debate_submission_role", type_="unique")
        batch.drop_column("delivery_status")
        batch.drop_column("submission_id")
    with op.batch_alter_table("debate_practice_records") as batch:
        batch.drop_constraint("uq_debate_active_key", type_="unique")
        batch.drop_column("report_started_at")
        batch.drop_column("report_status")
        batch.drop_column("active_key")
        batch.drop_column("is_legacy")
        batch.drop_column("flow_version")
    with op.batch_alter_table("interview_messages") as batch:
        batch.drop_constraint("uq_interview_submission_role", type_="unique")
        batch.drop_column("delivery_status")
        batch.drop_column("submission_id")
    with op.batch_alter_table("interview_practice_records") as batch:
        batch.drop_constraint("uq_interview_active_key", type_="unique")
        batch.drop_constraint("fk_interview_requested_scenario", type_="foreignkey")
        batch.drop_column("report_started_at")
        batch.drop_column("report_status")
        batch.drop_column("active_key")
        batch.drop_column("is_legacy")
        batch.drop_column("flow_version")
        batch.drop_column("requested_scenario_id")
