"""merge multiple heads

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9, d8e5f6a7b8c9, e8f5a4c3d2b1
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = ('d4e5f6a7b8c9', 'd8e5f6a7b8c9', 'e8f5a4c3d2b1')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cabinet_params',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cabinet_id', sa.Integer(), sa.ForeignKey('cabinets.id'), nullable=False, index=True),
        sa.Column('param_name', sa.String(200), nullable=False),
        sa.Column('param_value', sa.String(500), server_default=''),
        sa.Column('group_name', sa.String(100), server_default='default'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_cabinet_params_cabinet', 'cabinet_params', ['cabinet_id'])

    op.create_table(
        'chassis_params',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('chassis_id', sa.Integer(), sa.ForeignKey('test_chassis.id'), nullable=False, index=True),
        sa.Column('param_name', sa.String(200), nullable=False),
        sa.Column('param_value', sa.String(500), server_default=''),
        sa.Column('group_name', sa.String(100), server_default='default'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_chassis_params_chassis', 'chassis_params', ['chassis_id'])


def downgrade():
    op.drop_index('idx_chassis_params_chassis')
    op.drop_table('chassis_params')
    op.drop_index('idx_cabinet_params_cabinet')
    op.drop_table('cabinet_params')
