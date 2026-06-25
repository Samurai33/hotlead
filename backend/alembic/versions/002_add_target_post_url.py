"""add target_post_url to jobs

Revision ID: 002
Revises: 001
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column('target_post_url', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('jobs', 'target_post_url')
