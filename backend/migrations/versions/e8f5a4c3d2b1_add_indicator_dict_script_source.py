"""add script_source column to indicator_dict

Revision ID: e8f5a4c3d2b1
Revises: d7e5f4a3c2b9
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'e8f5a4c3d2b1'
down_revision = 'd7e5f4a3c2b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('indicator_dict', sa.Column('script_source', sa.Text(), nullable=False, server_default=''))


def downgrade():
    op.drop_column('indicator_dict', 'script_source')
