"""add_sub_scenario_metrics_and_binary_link

Revision ID: a1b2c3d4e5f6
Revises: 47712bb2651e
Create Date: 2026-07-12 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '47712bb2651e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sub_scenarios', sa.Column('metrics_json', sa.Text(), nullable=True))
    op.add_column('sub_scenarios', sa.Column('metrics_ini', sa.Text(), nullable=True))
    op.add_column('version_binary_files', sa.Column('sub_scenario_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_version_binary_files_sub_scenario_id'),
                     'version_binary_files', ['sub_scenario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_version_binary_files_sub_scenario_id'), table_name='version_binary_files')
    op.drop_column('version_binary_files', 'sub_scenario_id')
    op.drop_column('sub_scenarios', 'metrics_ini')
    op.drop_column('sub_scenarios', 'metrics_json')
