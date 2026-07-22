"""Create the original persistent application schema.

This migration is intentionally self-contained.  Importing the live ORM model
metadata here would make a fresh installation change whenever the models
change, and would make later migrations try to add columns that already exist.
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("yiban_id", sa.String(128), nullable=True, unique=True),
        sa.Column("phone", sa.String(20), nullable=True, unique=True),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("school", sa.String(100), nullable=True),
        sa.Column("college", sa.String(100), nullable=True),
        sa.Column("political_status", sa.String(50), nullable=True),
        sa.Column("role", sa.String(20), nullable=True),
        sa.Column("total_points", sa.Integer(), nullable=True),
        sa.Column("hashed_password", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "interview_scenarios",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("ai_role_name", sa.String(100), nullable=True),
        sa.Column("ai_role_title", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "history_scenarios",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("era", sa.String(100), nullable=True),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_estimate", sa.Integer(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "debate_topics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("pro_hint", sa.Text(), nullable=True),
        sa.Column("con_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "tour_sites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("emoji", sa.String(20), nullable=True),
        sa.Column("facts_json", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("is_template", sa.Boolean(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "community_posts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("is_question", sa.Boolean(), nullable=True),
        sa.Column("likes_count", sa.Integer(), nullable=True),
        sa.Column("replies_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "interview_practice_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario_id", sa.String(), sa.ForeignKey("interview_scenarios.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("total_rounds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("report_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "history_learning_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario_id", sa.String(), sa.ForeignKey("history_scenarios.id"), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "debate_practice_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("debate_topics.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("total_rounds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("stance", sa.String(20), nullable=True),
        sa.Column("feedback_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "tour_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("site_id", sa.String(), sa.ForeignKey("tour_sites.id"), nullable=False),
        sa.Column("qa_json", sa.Text(), nullable=True),
        sa.Column("report", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "generated_reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("report_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "teacher_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "community_replies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("post_id", sa.String(), sa.ForeignKey("community_posts.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_teacher", sa.Boolean(), nullable=True),
        sa.Column("likes_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "interview_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("record_id", sa.String(), sa.ForeignKey("interview_practice_records.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("analysis_json", sa.Text(), nullable=True),
        sa.Column("round_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "debate_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("record_id", sa.String(), sa.ForeignKey("debate_practice_records.id"), nullable=False),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    for table in (
        "debate_messages", "interview_messages", "community_replies",
        "teacher_tasks", "generated_reports", "tour_records",
        "debate_practice_records", "history_learning_records",
        "interview_practice_records", "community_posts", "knowledge_documents",
        "tour_sites", "debate_topics", "history_scenarios",
        "interview_scenarios", "users",
    ):
        op.drop_table(table)
