"""Add permission system: registration, user domains, audit log

Revision ID: d8e5f6a7b8c9
Revises: c9d4e3f2b1a7
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'd8e5f6a7b8c9'
down_revision = 'c9d4e3f2b1a7'
branch_labels = None
depends_on = None


def upgrade():
    # Add created_by column to users table
    op.add_column('users', sa.Column('created_by', sa.String(80), nullable=True))

    # Add registration_status column to users table
    op.add_column('users', sa.Column('registration_status', sa.String(20), nullable=False, server_default='active'))

    # Create account_registration table
    op.create_table('account_registration',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(80), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('requested_role', sa.String(20), nullable=False, default='operator'),
        sa.Column('requested_domains', sa.JSON, nullable=True),
        sa.Column('justification', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('reviewer_id', sa.Integer, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('review_comment', sa.Text, nullable=True),
    )

    # Create user_domain table
    op.create_table('user_domain',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('domain', sa.String(50), nullable=False),
        sa.UniqueConstraint('user_id', 'domain', name='uq_user_domain'),
    )

    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('username', sa.String(80), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('detail', sa.JSON, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])

    # Create indexes
    op.create_index('idx_user_domain_user_id', 'user_domain', ['user_id'])
    op.create_index('idx_registration_status', 'account_registration', ['status'])
    op.create_index('idx_registration_username', 'account_registration', ['username'])


def downgrade():
    op.drop_index('idx_registration_username', table_name='account_registration')
    op.drop_index('idx_registration_status', table_name='account_registration')
    op.drop_index('idx_user_domain_user_id', table_name='user_domain')
    op.drop_index('idx_audit_log_created_at', table_name='audit_log')
    op.drop_index('idx_audit_log_action', table_name='audit_log')
    op.drop_index('idx_audit_log_user_id', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('user_domain')
    op.drop_table('account_registration')
    op.drop_column('users', 'registration_status')
    op.drop_column('users', 'created_by')
