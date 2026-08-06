"""Repair terminal training steps migrated from legacy records."""

from alembic import op


revision = "0008_training_data_repair"
down_revision = "0007_training_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    # Legacy quick debates stored the last zero-based step (3) even after the
    # fourth answer had been accepted. Terminal sessions expose a completed
    # step count so progress cannot fall back from 100% after a restart.
    op.execute("""
        UPDATE debate_practice_records
        SET current_step = 4
        WHERE mode = 'quick'
          AND current_stage = 'finished'
          AND current_step < 4
    """)
    op.execute("""
        UPDATE debate_practice_records
        SET current_step = 6
        WHERE mode = 'full'
          AND current_stage = 'finished'
          AND current_step < 6
    """)


def downgrade():
    # This migration only normalizes derived counters; reverting would
    # deliberately reintroduce the progress bug.
    pass
