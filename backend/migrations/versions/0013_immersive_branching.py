"""Add server-controlled branching state to immersive books."""

from alembic import op
import sqlalchemy as sa


revision = "0013_immersive_branching"
down_revision = "0012_community_collaboration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("immersive_books") as batch:
        batch.add_column(sa.Column("graph_json", sa.Text(), server_default="{}", nullable=False))
    with op.batch_alter_table("immersive_progress") as batch:
        batch.add_column(sa.Column("current_spread_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("route_state_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("flow_version", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("immersive_progress") as batch:
        batch.drop_column("flow_version")
        batch.drop_column("route_state_json")
        batch.drop_column("current_spread_id")
    with op.batch_alter_table("immersive_books") as batch:
        batch.drop_column("graph_json")

