"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('language_code', sa.String(10), nullable=True, server_default='ru'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('ix_users_username', 'users', ['username'])
    
    # Create daily_limits table
    op.create_table(
        'daily_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('text_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('image_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('voice_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text_limit', sa.Integer(), nullable=True),
        sa.Column('image_limit', sa.Integer(), nullable=True),
        sa.Column('video_limit', sa.Integer(), nullable=True),
        sa.Column('voice_limit', sa.Integer(), nullable=True),
        sa.Column('document_limit', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_daily_limit')
    )
    op.create_index('ix_daily_limits_user_date', 'daily_limits', ['user_id', 'date'])
    
    # Create requests table
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('response_preview', sa.Text(), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_requests_user_id', 'requests', ['user_id'])
    op.create_index('ix_requests_created_at', 'requests', ['created_at'])
    op.create_index('ix_requests_type_status', 'requests', ['request_type', 'status'])
    
    # Create video_tasks table
    op.create_table(
        'video_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(50), nullable=False, server_default='sora-2'),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('openai_video_id', sa.String(255), nullable=True),
        sa.Column('result_file_id', sa.String(255), nullable=True),
        sa.Column('reference_image_file_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_video_tasks_user_id', 'video_tasks', ['user_id'])
    op.create_index('ix_video_tasks_status', 'video_tasks', ['status'])
    
    # Create admins table
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create settings table
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_table('admins')
    op.drop_table('video_tasks')
    op.drop_table('requests')
    op.drop_table('daily_limits')
    op.drop_table('users')
