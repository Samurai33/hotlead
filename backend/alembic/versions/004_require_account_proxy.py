"""require accounts.proxy_url (audit C1)

session_json's encryption (audit C2) needs no schema change -- Fernet output
is still stored as TEXT, encryption/decryption happens transparently in the
EncryptedText TypeDecorator (app/core/crypto.py), not at the DB layer.

Revision ID: 004
Revises: 003
Create Date: 2026-08-09

"""

from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('accounts', 'proxy_url', existing_type=sa.String(500), nullable=False)


def downgrade() -> None:
    op.alter_column('accounts', 'proxy_url', existing_type=sa.String(500), nullable=True)
