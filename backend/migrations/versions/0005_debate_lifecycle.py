"""Add private AI topics and structured debate stages."""
from alembic import op
import sqlalchemy as sa

revision="0005_debate_lifecycle"; down_revision="0004_history_scenarios"; branch_labels=None; depends_on=None

def upgrade():
    with op.batch_alter_table("debate_topics") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(), nullable=True)); batch.add_column(sa.Column("status", sa.String(20), server_default="published", nullable=False)); batch.create_foreign_key("fk_debate_topic_owner", "users", ["owner_id"], ["id"])
    with op.batch_alter_table("debate_practice_records") as batch:
        batch.add_column(sa.Column("current_stage", sa.String(30), server_default="opening", nullable=False))

def downgrade():
    with op.batch_alter_table("debate_practice_records") as batch: batch.drop_column("current_stage")
    with op.batch_alter_table("debate_topics") as batch: batch.drop_constraint("fk_debate_topic_owner", type_="foreignkey"); batch.drop_column("status"); batch.drop_column("owner_id")
