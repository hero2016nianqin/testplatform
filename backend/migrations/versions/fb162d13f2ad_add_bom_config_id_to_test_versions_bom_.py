"""add bom_config_id to test_versions, bom_snapshot to sub_scenarios, bom_indicator_data to software_configs

Revision ID: fb162d13f2ad
Revises: g7h8i9j0k1l2
Create Date: 2026-08-23 19:01:27.183598
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb162d13f2ad'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not column_exists('software_configs', 'bom_indicator_data'):
        op.add_column('software_configs', sa.Column('bom_indicator_data', sa.JSON(), nullable=True))
    if not column_exists('sub_scenarios', 'bom_snapshot'):
        op.add_column('sub_scenarios', sa.Column('bom_snapshot', sa.JSON(), nullable=True))
    if not column_exists('test_versions', 'bom_config_id'):
        op.add_column('test_versions', sa.Column('bom_config_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    if column_exists('test_versions', 'bom_config_id'):
        op.drop_column('test_versions', 'bom_config_id')
    if column_exists('sub_scenarios', 'bom_snapshot'):
        op.drop_column('sub_scenarios', 'bom_snapshot')
    if column_exists('software_configs', 'bom_indicator_data'):
        op.drop_column('software_configs', 'bom_indicator_data')
