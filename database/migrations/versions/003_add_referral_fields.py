"""Add referral system fields to users table.

Revision ID: 003_add_referral
Revises: 002_add_enum
Create Date: 2026-02-13 12:00:00.000000

Adds referred_by, referral_code, referral_earnings columns to the users table
for the referral/cashback system.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_referral'
down_revision: Union[str, None] = '002_add_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add referral columns to users table
    op.add_column('users', sa.Column('referred_by', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('referral_code', sa.String(32), nullable=True))
    op.add_column('users', sa.Column('referral_earnings', sa.Numeric(10, 2), server_default='0', nullable=False))
    
    # Add unique constraint on referral_code
    op.create_index('ix_users_referral_code', 'users', ['referral_code'], unique=True)
    op.create_index('ix_users_referred_by', 'users', ['referred_by'])


def downgrade() -> None:
    op.drop_index('ix_users_referred_by', table_name='users')
    op.drop_index('ix_users_referral_code', table_name='users')
    op.drop_column('users', 'referral_earnings')
    op.drop_column('users', 'referral_code')
    op.drop_column('users', 'referred_by')
