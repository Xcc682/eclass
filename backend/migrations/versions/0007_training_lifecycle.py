"""Add deterministic interview and debate training lifecycle fields."""
from alembic import op
import sqlalchemy as sa

revision = "0007_training_lifecycle"
down_revision = "0006_immersive_books"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("interview_practice_records") as batch:
        batch.add_column(sa.Column("current_phase", sa.String(40), server_default="开场寒暄", nullable=False))
        batch.add_column(sa.Column("current_step", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("live_evaluation_json", sa.Text(), server_default="{}", nullable=False))

    # Existing records did not persist phase state. Derive the current question
    # from the number of accepted user answers without rewriting old messages.
    op.execute("""
        UPDATE interview_practice_records
        SET current_step = (
            SELECT CASE
                WHEN COUNT(*) > 5 THEN 5
                ELSE CAST(COUNT(*) AS INTEGER)
            END
            FROM interview_messages m
            WHERE m.record_id = interview_practice_records.id AND m.role = 'user'
        )
    """)
    op.execute("""
        UPDATE interview_practice_records
        SET current_phase = CASE current_step
            WHEN 0 THEN '开场寒暄'
            WHEN 1 THEN '自我认知'
            WHEN 2 THEN '入党动机'
            WHEN 3 THEN '理论考察'
            WHEN 4 THEN '理论考察'
            ELSE '情景假设' END
    """)

    with op.batch_alter_table("debate_practice_records") as batch:
        batch.add_column(sa.Column("mode", sa.String(20), server_default="quick", nullable=False))
        batch.add_column(sa.Column("current_step", sa.Integer(), server_default="0", nullable=False))
    op.execute("""
        UPDATE debate_practice_records
        SET current_step = (
            SELECT CASE
                WHEN COUNT(*) > 4 THEN 4
                ELSE CAST(COUNT(*) AS INTEGER)
            END
            FROM debate_messages m
            WHERE m.record_id = debate_practice_records.id AND m.role = 'user'
        )
    """)
    op.execute("""
        UPDATE debate_practice_records
        SET status = 'awaiting_feedback'
        WHERE current_stage = 'finished' AND feedback_json IS NULL
    """)

    with op.batch_alter_table("debate_messages") as batch:
        batch.add_column(sa.Column("analysis_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("evidence_json", sa.Text(), server_default="[]", nullable=False))

    with op.batch_alter_table("generated_reports") as batch:
        batch.add_column(sa.Column("source_record_id", sa.String(), nullable=True))
        batch.create_index("ix_generated_reports_source_record_id", ["source_record_id"], unique=False)
        batch.create_unique_constraint("uq_generated_report_source", ["report_type", "source_record_id"])


def downgrade():
    with op.batch_alter_table("generated_reports") as batch:
        batch.drop_constraint("uq_generated_report_source", type_="unique")
        batch.drop_index("ix_generated_reports_source_record_id")
        batch.drop_column("source_record_id")
    with op.batch_alter_table("debate_messages") as batch:
        batch.drop_column("evidence_json")
        batch.drop_column("analysis_json")
    with op.batch_alter_table("debate_practice_records") as batch:
        batch.drop_column("current_step")
        batch.drop_column("mode")
    with op.batch_alter_table("interview_practice_records") as batch:
        batch.drop_column("live_evaluation_json")
        batch.drop_column("current_step")
        batch.drop_column("current_phase")
