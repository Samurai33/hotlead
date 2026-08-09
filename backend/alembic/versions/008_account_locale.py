"""add accounts.locale for proxy geo-matching (audit AUDIT-2.md M5)

Revision ID: 008
Revises: 007
Create Date: 2026-08-09

"""

from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column('locale', sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'locale')
