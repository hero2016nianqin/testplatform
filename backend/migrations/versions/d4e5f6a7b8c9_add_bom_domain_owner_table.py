"""add_bom_domain_owner_table

Revision ID: d4e5f6a7b8c9
Revises: a3b1c9d2e4f5
Create Date: 2026-08-01 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'a3b1c9d2e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bom_domain_owner',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bom_code', sa.String(length=100), nullable=False),
        sa.Column('domain_owners', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bom_code')
    )
    op.create_index('ix_bom_domain_owner_bom_code', 'bom_domain_owner', ['bom_code'])


def downgrade() -> None:
    op.drop_index('ix_bom_domain_owner_bom_code', table_name='bom_domain_owner')
    op.drop_table('bom_domain_owner')