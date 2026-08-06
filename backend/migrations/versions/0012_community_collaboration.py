"""Turn the community prototype into a reliable learning collaboration hub."""

from alembic import op
import sqlalchemy as sa


revision = "0012_community_collaboration"
down_revision = "0011_knowledge_qa_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("community_posts") as batch:
        batch.add_column(sa.Column("favorites_count", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("moderation_status", sa.String(20), server_default="published", nullable=False))
        batch.add_column(sa.Column("moderation_reason", sa.Text(), server_default="", nullable=False))
        batch.add_column(sa.Column("pinned", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("submission_id", sa.String(64), nullable=True))
        batch.create_index("ix_community_posts_user_id", ["user_id"])
        batch.create_index("ix_community_posts_category", ["category"])
        batch.create_index("ix_community_posts_is_question", ["is_question"])
        batch.create_index("ix_community_posts_status", ["status"])
        batch.create_index("ix_community_posts_moderation_status", ["moderation_status"])
        batch.create_unique_constraint("uq_community_post_submission", ["user_id", "submission_id"])

    with op.batch_alter_table("community_replies") as batch:
        batch.add_column(sa.Column("parent_reply_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(20), server_default="active", nullable=False))
        batch.add_column(sa.Column("submission_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_community_reply_parent", "community_replies", ["parent_reply_id"], ["id"])
        batch.create_index("ix_community_replies_user_id", ["user_id"])
        batch.create_index("ix_community_replies_parent_reply_id", ["parent_reply_id"])
        batch.create_index("ix_community_replies_status", ["status"])
        batch.create_unique_constraint("uq_community_reply_submission", ["post_id", "user_id", "submission_id"])
    op.execute("UPDATE community_replies SET updated_at = created_at WHERE updated_at IS NULL")

    with op.batch_alter_table("teacher_tasks") as batch:
        batch.add_column(sa.Column("deadline_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE teacher_tasks SET status = 'published' WHERE status = 'active'")
    op.execute("UPDATE teacher_tasks SET updated_at = created_at WHERE updated_at IS NULL")

    with op.batch_alter_table("task_submissions") as batch:
        batch.add_column(sa.Column("next_step", sa.Text(), server_default="", nullable=False))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE task_submissions SET updated_at = submitted_at WHERE updated_at IS NULL")

    op.create_table(
        "community_favorites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_id", sa.String(), sa.ForeignKey("community_posts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "post_id", name="uq_community_favorite"),
    )
    op.create_index("ix_community_favorites_user_id", "community_favorites", ["user_id"])
    op.create_index("ix_community_favorites_post_id", "community_favorites", ["post_id"])

    op.create_table(
        "community_reply_likes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reply_id", sa.String(), sa.ForeignKey("community_replies.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "reply_id", name="uq_community_reply_like"),
    )
    op.create_index("ix_community_reply_likes_user_id", "community_reply_likes", ["user_id"])
    op.create_index("ix_community_reply_likes_reply_id", "community_reply_likes", ["reply_id"])

    op.create_table(
        "community_topic_follows",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "topic", name="uq_community_topic_follow"),
    )
    op.create_index("ix_community_topic_follows_user_id", "community_topic_follows", ["user_id"])
    op.create_index("ix_community_topic_follows_topic", "community_topic_follows", ["topic"])

    op.create_table(
        "community_notifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.String(500), server_default="", nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "event_key", name="uq_community_notification_event"),
    )
    op.create_index("ix_community_notification_user_read", "community_notifications", ["user_id", "is_read", "created_at"])

    op.create_table(
        "community_content_reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("reporter_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("detail", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reviewer_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_community_report_target"),
    )
    op.create_index("ix_community_content_reports_reporter_id", "community_content_reports", ["reporter_id"])
    op.create_index("ix_community_content_reports_target_id", "community_content_reports", ["target_id"])
    op.create_index("ix_community_content_reports_status", "community_content_reports", ["status"])

    op.create_table(
        "community_attachments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("original_name", sa.String(300), nullable=False),
        sa.Column("storage_key", sa.String(600), nullable=False, unique=True),
        sa.Column("storage_backend", sa.String(20), server_default="local", nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="temporary", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    for column in ("owner_id", "target_type", "target_id", "status"):
        op.create_index(f"ix_community_attachments_{column}", "community_attachments", [column])

    op.create_table(
        "community_post_views",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_id", sa.String(), sa.ForeignKey("community_posts.id"), nullable=False),
        sa.Column("view_bucket", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "post_id", "view_bucket", name="uq_community_post_view_bucket"),
    )
    op.create_index("ix_community_post_views_user_id", "community_post_views", ["user_id"])
    op.create_index("ix_community_post_views_post_id", "community_post_views", ["post_id"])

    op.create_table(
        "task_rubric_criteria",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("teacher_tasks.id"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_task_rubric_criteria_task_id", "task_rubric_criteria", ["task_id"])
    op.create_table(
        "task_rubric_scores",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("task_submissions.id"), nullable=False),
        sa.Column("criterion_id", sa.String(), sa.ForeignKey("task_rubric_criteria.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), server_default="", nullable=False),
        sa.UniqueConstraint("submission_id", "criterion_id", name="uq_task_rubric_score"),
    )
    op.create_index("ix_task_rubric_scores_submission_id", "task_rubric_scores", ["submission_id"])
    op.create_index("ix_task_rubric_scores_criterion_id", "task_rubric_scores", ["criterion_id"])

    # Archive only unmistakable automated fixtures; retain every real user post.
    op.execute("UPDATE community_posts SET status = 'archived' WHERE title = '自动化验收帖子' AND category = '测试'")


def downgrade() -> None:
    op.drop_table("task_rubric_scores")
    op.drop_table("task_rubric_criteria")
    op.drop_table("community_post_views")
    op.drop_table("community_attachments")
    op.drop_table("community_content_reports")
    op.drop_table("community_notifications")
    op.drop_table("community_topic_follows")
    op.drop_table("community_reply_likes")
    op.drop_table("community_favorites")
    with op.batch_alter_table("task_submissions") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("next_step")
    with op.batch_alter_table("teacher_tasks") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("deadline_at")
    with op.batch_alter_table("community_replies") as batch:
        batch.drop_constraint("uq_community_reply_submission", type_="unique")
        batch.drop_constraint("fk_community_reply_parent", type_="foreignkey")
        batch.drop_index("ix_community_replies_parent_reply_id")
        batch.drop_index("ix_community_replies_status")
        batch.drop_index("ix_community_replies_user_id")
        batch.drop_column("updated_at")
        batch.drop_column("submission_id")
        batch.drop_column("status")
        batch.drop_column("parent_reply_id")
    with op.batch_alter_table("community_posts") as batch:
        batch.drop_constraint("uq_community_post_submission", type_="unique")
        batch.drop_index("ix_community_posts_moderation_status")
        batch.drop_index("ix_community_posts_status")
        batch.drop_index("ix_community_posts_is_question")
        batch.drop_index("ix_community_posts_category")
        batch.drop_index("ix_community_posts_user_id")
        batch.drop_column("submission_id")
        batch.drop_column("pinned")
        batch.drop_column("moderation_reason")
        batch.drop_column("moderation_status")
        batch.drop_column("favorites_count")
