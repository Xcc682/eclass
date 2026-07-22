"""Add real scenario content and persisted learning interactions."""
from alembic import op
import sqlalchemy as sa


revision = "0004_history_scenarios"
down_revision = "0003_community_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("history_scenarios") as batch:
        batch.add_column(sa.Column("background", sa.Text(), server_default="", nullable=False))
        batch.add_column(sa.Column("knowledge_points_json", sa.Text(), server_default="[]", nullable=False))
        batch.add_column(sa.Column("decision_points_json", sa.Text(), server_default="{}", nullable=False))
    with op.batch_alter_table("history_learning_records") as batch:
        batch.add_column(sa.Column("choice_index", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("qa_json", sa.Text(), server_default="[]", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("history_learning_records") as batch:
        batch.drop_column("qa_json"); batch.drop_column("choice_index")
    with op.batch_alter_table("history_scenarios") as batch:
        batch.drop_column("decision_points_json"); batch.drop_column("knowledge_points_json"); batch.drop_column("background")
