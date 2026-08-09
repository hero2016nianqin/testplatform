"""add test_params column to indicator_dict

Revision ID: d7e5f4a3c2b9
Revises: c9d4e3f2b1a7
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e5f4a3c2b9'
down_revision = 'c9d4e3f2b1a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('indicator_dict', sa.Column('test_params', sa.JSON(), nullable=False, server_default='[]'))


def downgrade():
    op.drop_column('indicator_dict', 'test_params')
