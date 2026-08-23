"""add serial_number to test_slots

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'g7h8i9j0k1l2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('test_slots', sa.Column('serial_number', sa.String(200), nullable=True))

def downgrade() -> None:
    op.drop_column('test_slots', 'serial_number')
