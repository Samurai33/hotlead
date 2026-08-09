"""add indexes for created_at (jobs/accounts/prospects) and prospects.followers (audit AUDIT-2.md M10)

Revision ID: 007
Revises: 006
Create Date: 2026-08-09

"""

from alembic import op

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_accounts_created_at', 'accounts', ['created_at'])
    op.create_index('ix_prospects_created_at', 'prospects', ['created_at'])
    op.create_index('ix_prospects_followers', 'prospects', ['followers'])


def downgrade() -> None:
    op.drop_index('ix_prospects_followers', table_name='prospects')
    op.drop_index('ix_prospects_created_at', table_name='prospects')
    op.drop_index('ix_accounts_created_at', table_name='accounts')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
