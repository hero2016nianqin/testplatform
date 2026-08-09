"""add params column to bom_indicator

Revision ID: c9d4e3f2b1a7
Revises: b8e3c2d1a4f5
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c9d4e3f2b1a7'
down_revision = 'b8e3c2d1a4f5'
branch_labels = None
depends_on = None


def upgrade():
    # Add params JSON column to bom_indicator (default empty array)
    op.add_column('bom_indicator', sa.Column('params', sa.JSON(), nullable=False, server_default='[]'))

    # Backfill: copy each indicator's dict params into bom_indicator.params
    # Handle old format (dict) and new format (list)
    import json
    conn = op.get_bind()
    rows = conn.execute(text("SELECT bi.id, idict.params FROM bom_indicator bi JOIN indicator_dict idict ON idict.id = bi.indicator_id")).fetchall()
    for row_id, raw_params in rows:
        if not raw_params:
            continue
        parsed = json.loads(raw_params) if isinstance(raw_params, str) else raw_params
        if isinstance(parsed, dict):
            arr = [{"param_key": k, "param_name": k, "param_value": str(v), "param_type": "通用测试参数", "remark": ""} for k, v in parsed.items()]
        elif isinstance(parsed, list):
            arr = parsed
        else:
            arr = []
        conn.execute(text("UPDATE bom_indicator SET params = :p WHERE id = :id"), {"p": json.dumps(arr), "id": row_id})


def downgrade():
    op.drop_column('bom_indicator', 'params')
