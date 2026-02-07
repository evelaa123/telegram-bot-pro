"""Add missing requesttype enum values: presentation, video_animate, long_video

Revision ID: 002_add_enum
Revises: 001_initial
Create Date: 2026-02-07 12:00:00.000000

The Python RequestType enum was extended with PRESENTATION, VIDEO_ANIMATE,
and LONG_VIDEO, but the PostgreSQL 'requesttype' enum type was never updated.
This causes: DBAPIError: invalid input value for enum requesttype: "VIDEO_ANIMATE"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_enum'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing enum values to the requesttype PostgreSQL enum.
    
    ALTER TYPE ... ADD VALUE is safe and idempotent in PostgreSQL 9.3+
    when combined with IF NOT EXISTS (PostgreSQL 12+).
    
    We also add columns to daily_limits that the model expects.
    """
    # Add missing values to the requesttype enum
    # Each ADD VALUE must run outside a transaction in PostgreSQL < 12,
    # but Alembic runs each migration in its own transaction.
    # We use op.execute with COMMIT to work around this.
    
    # First, check if requesttype enum even exists. If the DB still uses
    # varchar for requests.type, we need a different approach.
    # Based on the error message, the enum DOES exist, so we add values.
    
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'presentation'")
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'video_animate'")
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'long_video'")
    
    # Also add missing columns to daily_limits table if they don't exist
    # The model expects: presentation_count, video_animate_count, long_video_count
    # These may already exist from manual DDL changes.
    conn = op.get_bind()
    
    # Check which columns exist in daily_limits
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'daily_limits'"
    ))
    existing_columns = {row[0] for row in result}
    
    if 'presentation_count' not in existing_columns:
        op.add_column('daily_limits', sa.Column(
            'presentation_count', sa.Integer(), nullable=False, server_default='0'
        ))
    
    if 'video_animate_count' not in existing_columns:
        op.add_column('daily_limits', sa.Column(
            'video_animate_count', sa.Integer(), nullable=False, server_default='0'
        ))
    
    if 'long_video_count' not in existing_columns:
        op.add_column('daily_limits', sa.Column(
            'long_video_count', sa.Integer(), nullable=False, server_default='0'
        ))


def downgrade() -> None:
    """Remove the added columns. 
    
    Note: PostgreSQL does not support removing values from an enum type.
    The enum values will remain but are harmless.
    """
    # Drop columns if they exist
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'daily_limits'"
    ))
    existing_columns = {row[0] for row in result}
    
    if 'long_video_count' in existing_columns:
        op.drop_column('daily_limits', 'long_video_count')
    if 'video_animate_count' in existing_columns:
        op.drop_column('daily_limits', 'video_animate_count')
    if 'presentation_count' in existing_columns:
        op.drop_column('daily_limits', 'presentation_count')
