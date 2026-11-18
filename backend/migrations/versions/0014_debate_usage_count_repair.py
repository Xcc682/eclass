"""Backfill debate topic counters so usage_count can no longer be NULL.

The initial migration created debate_topics.usage_count as a nullable column
without a server default, and the seed rows insert without setting it. Seeded
topics therefore carried NULL, and starting a debate on one raised
``TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'``
(returning HTTP 500) instead of incrementing the counter.
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_debate_usage_count_repair"
down_revision = "0013_immersive_branching"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE debate_topics SET usage_count = 0 WHERE usage_count IS NULL")
    with op.batch_alter_table("debate_topics") as batch:
        batch.alter_column(
            "usage_count",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="0",
        )


def downgrade() -> None:
    with op.batch_alter_table("debate_topics") as batch:
        batch.alter_column(
            "usage_count",
            existing_type=sa.Integer(),
            nullable=True,
            server_default=None,
        )
