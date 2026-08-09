"""add accounts.leased_until (audit AUDIT-2.md H4)

Revision ID: 006
Revises: 005
Create Date: 2026-08-09

"""

from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column('leased_until', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'leased_until')
