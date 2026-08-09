"""add accounts.challenge_streak (audit AUDIT-2.md H3)

Revision ID: 005
Revises: 004
Create Date: 2026-08-09

"""

from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column('challenge_streak', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'challenge_streak')
