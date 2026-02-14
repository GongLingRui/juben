"""初始化数据库 schema

Revision ID: 001_initial
Revises:
Create Date: 2026-02-09

匹配 0001_init.sql 中的表结构
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建所有表 - 匹配 0001_init.sql"""

    # 启用 pgcrypto 扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    # 用户会话表
    op.create_table(
        'user_sessions',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('user_id', 'session_id')
    )

    # 聊天消息表
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=True),
        sa.Column('message_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_user_session_created_at', 'chat_messages',
                    ['user_id', 'session_id', sa.text('created_at DESC')])

    # 上下文状态表
    op.create_table(
        'context_states',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('context_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('context_type', sa.String(), nullable=False, server_default='general'),
        sa.Column('context_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('user_id', 'session_id', 'agent_name')
    )

    # 笔记表
    op.create_table(
        'notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('cover_title', sa.String(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('select_status', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_comment', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'session_id', 'action', 'name')
    )
    op.create_index('idx_notes_user_session_created_at', 'notes',
                    ['user_id', 'session_id', sa.text('created_at DESC')])

    # Token 使用表
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=True),
        sa.Column('model_provider', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('request_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_points', sa.Float(), nullable=False, server_default='0'),
        sa.Column('request_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('billing_summary', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_token_usage_user_session', 'token_usage', ['user_id', 'session_id'])

    # 流事件表
    op.create_table(
        'stream_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('agent_source', sa.String(), nullable=True),
        sa.Column('event_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('event_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_replayed', sa.Boolean(), nullable=False, server_default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stream_events_user_session_created_at', 'stream_events',
                    ['user_id', 'session_id', sa.text('created_at DESC')])

    # 审计日志表
    op.create_table(
        'audit_logs',
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', [sa.text('timestamp DESC')])
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id', sa.text('timestamp DESC')])

    # 缓存存储表
    op.create_table(
        'cache_store',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.LargeBinary(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('key')
    )

    # 工作流表
    op.create_table(
        'workflows',
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('workflow_id')
    )

    # 工作流版本表
    op.create_table(
        'workflow_versions',
        sa.Column('version_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('version_number', sa.String(), nullable=False),
        sa.Column('definition', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('parent_version_id', sa.String(), nullable=True),
        sa.Column('commit_message', sa.String(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.PrimaryKeyConstraint('version_id')
    )
    op.create_index('idx_workflow_versions_workflow', 'workflow_versions',
                    ['workflow_id', sa.text('created_at DESC')])

    # 工作流分支表
    op.create_table(
        'workflow_branches',
        sa.Column('branch_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('branch_name', sa.String(), nullable=False),
        sa.Column('head_version_id', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('branch_id'),
        sa.UniqueConstraint('workflow_id', 'branch_name')
    )
    op.create_index('idx_workflow_branches_workflow', 'workflow_branches', ['workflow_id'])


def downgrade() -> None:
    """删除所有表 - 按依赖关系倒序"""
    op.drop_table('workflow_branches')
    op.drop_table('workflow_versions')
    op.drop_table('workflows')
    op.drop_table('cache_store')
    op.drop_table('audit_logs')
    op.drop_table('stream_events')
    op.drop_table('token_usage')
    op.drop_table('notes')
    op.drop_table('context_states')
    op.drop_table('chat_messages')
    op.drop_table('user_sessions')
