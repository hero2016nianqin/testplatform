"""add_review_archive_fields

Revision ID: 1a8d34795881
Revises: 2becf6dc8b9f
Create Date: 2026-07-24 20:38:22.090254
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a8d34795881'
down_revision: Union[str, None] = '2becf6dc8b9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bom_config', sa.Column('review_status', sa.String(length=20), nullable=False, server_default='none'))
    op.add_column('bom_config', sa.Column('review_comment', sa.Text(), nullable=True))
    op.add_column('bom_config', sa.Column('review_operator', sa.String(length=100), nullable=True))
    op.add_column('bom_config', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('bom_config', sa.Column('archived', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('bom_config', sa.Column('archived_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('bom_config', 'archived_at')
    op.drop_column('bom_config', 'archived')
    op.drop_column('bom_config', 'reviewed_at')
    op.drop_column('bom_config', 'review_operator')
    op.drop_column('bom_config', 'review_comment')
    op.drop_column('bom_config', 'review_status')
