"""add_domain_fields

Revision ID: a3b1c9d2e4f5
Revises: c7f8cb373a0c
Create Date: 2026-08-01 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b1c9d2e4f5'
down_revision: Union[str, None] = 'c7f8cb373a0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('indicator_dict', sa.Column('domain', sa.String(length=50), server_default='', nullable=False))
    op.add_column('bom_config', sa.Column('domain_owners', sa.JSON(), server_default='{}', nullable=False))


def downgrade() -> None:
    op.drop_column('bom_config', 'domain_owners')
    op.drop_column('indicator_dict', 'domain')
