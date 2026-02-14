-- Initial schema for Juben (PostgreSQL)

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS user_sessions (
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, session_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  message_type TEXT NOT NULL,
  content TEXT NOT NULL,
  agent_name TEXT,
  message_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_session_created_at
  ON chat_messages (user_id, session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS context_states (
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  context_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  context_type TEXT NOT NULL DEFAULT 'general',
  context_version INT NOT NULL DEFAULT 1,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  PRIMARY KEY (user_id, session_id, agent_name)
);

CREATE TABLE IF NOT EXISTS notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  action TEXT NOT NULL,
  name TEXT NOT NULL,
  title TEXT,
  cover_title TEXT,
  content_type TEXT,
  context TEXT NOT NULL,
  select_status INT NOT NULL DEFAULT 0,
  user_comment TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, session_id, action, name)
);

CREATE INDEX IF NOT EXISTS idx_notes_user_session_created_at
  ON notes (user_id, session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS token_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  agent_name TEXT,
  model_provider TEXT,
  model_name TEXT,
  request_tokens INT NOT NULL DEFAULT 0,
  response_tokens INT NOT NULL DEFAULT 0,
  total_tokens INT NOT NULL DEFAULT 0,
  cost_points DOUBLE PRECISION NOT NULL DEFAULT 0,
  request_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  billing_summary JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_token_usage_user_session
  ON token_usage (user_id, session_id);

CREATE TABLE IF NOT EXISTS stream_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  content_type TEXT,
  agent_source TEXT,
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_replayed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stream_events_user_session_created_at
  ON stream_events (user_id, session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  user_id TEXT,
  session_id TEXT,
  ip_address TEXT,
  user_agent TEXT,
  action TEXT,
  resource_type TEXT,
  resource_id TEXT,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  success BOOLEAN NOT NULL DEFAULT TRUE,
  error_message TEXT,
  correlation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs (user_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS cache_store (
  key TEXT PRIMARY KEY,
  value BYTEA NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflows (
  workflow_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_versions (
  version_id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL,
  version_number TEXT NOT NULL,
  definition JSONB NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by TEXT,
  parent_version_id TEXT,
  commit_message TEXT,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_workflow_versions_workflow
  ON workflow_versions (workflow_id, created_at DESC);

CREATE TABLE IF NOT EXISTS workflow_branches (
  branch_id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL,
  branch_name TEXT NOT NULL,
  head_version_id TEXT NOT NULL,
  created_by TEXT,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workflow_id, branch_name)
);

CREATE INDEX IF NOT EXISTS idx_workflow_branches_workflow
  ON workflow_branches (workflow_id);
