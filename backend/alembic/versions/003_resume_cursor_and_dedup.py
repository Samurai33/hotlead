"""add jobs.scrape_cursor, unique (job_id, ig_pk) on prospects

Revision ID: 003
Revises: 002
Create Date: 2026-08-09

"""

from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column('scrape_cursor', sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        'uq_prospects_job_id_ig_pk', 'prospects', ['job_id', 'ig_pk']
    )


def downgrade() -> None:
    op.drop_constraint('uq_prospects_job_id_ig_pk', 'prospects', type_='unique')
    op.drop_column('jobs', 'scrape_cursor')
