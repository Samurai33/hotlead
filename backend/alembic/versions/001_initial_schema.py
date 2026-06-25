"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-06-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table('jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('profile_username', sa.String(100), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False, server_default='followers'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_count',   sa.Integer, nullable=False, server_default='0'),
        sa.Column('scraped_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('emails_found',  sa.Integer, nullable=False, server_default='0'),
        sa.Column('phones_found',  sa.Integer, nullable=False, server_default='0'),
        sa.Column('celery_task_id', sa.String(200), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_jobs_profile_username', 'jobs', ['profile_username'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])

    op.create_table('accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(150), unique=True, nullable=False),
        sa.Column('session_json', sa.Text, nullable=True),
        sa.Column('proxy_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('requests_today', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_used_at',   sa.DateTime(timezone=True), nullable=True),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_accounts_status', 'accounts', ['status'])

    op.create_table('prospects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('username',    sa.String(150), nullable=False),
        sa.Column('full_name',   sa.String(255), nullable=True),
        sa.Column('ig_pk',       sa.String(50),  nullable=True),
        sa.Column('email',       sa.String(320), nullable=True),
        sa.Column('phone',       sa.String(50),  nullable=True),
        sa.Column('website',     sa.String(500), nullable=True),
        sa.Column('biography',   sa.Text,        nullable=True),
        sa.Column('followers',   sa.Integer, nullable=False, server_default='0'),
        sa.Column('following',   sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_business', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_private',  sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_prospects_job_id', 'prospects', ['job_id'])
    op.create_index('ix_prospects_email', 'prospects', ['email'])
    op.create_index('ix_prospects_job_email', 'prospects', ['job_id', 'email'])


def downgrade() -> None:
    op.drop_table('prospects')
    op.drop_table('accounts')
    op.drop_table('jobs')
