"""add_process_station_fields

Revision ID: c7f8cb373a0c
Revises: e8f5a4c3d2b1
Create Date: 2026-07-28 04:31:05.309195
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f8cb373a0c'
down_revision: Union[str, None] = 'e8f5a4c3d2b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bom_indicator', sa.Column('process_name', sa.String(length=100), server_default='', nullable=False))
    op.add_column('bom_indicator', sa.Column('station_name', sa.String(length=100), server_default='', nullable=False))
    op.add_column('collection_test_item', sa.Column('process_name', sa.String(length=100), server_default='', nullable=False))


def downgrade() -> None:
    op.drop_column('collection_test_item', 'process_name')
    op.drop_column('bom_indicator', 'station_name')
    op.drop_column('bom_indicator', 'process_name')
