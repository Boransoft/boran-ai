CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id VARCHAR(128) NOT NULL UNIQUE,
  username VARCHAR(64) UNIQUE,
  email VARCHAR(255) UNIQUE,
  hashed_password VARCHAR(255),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  display_name VARCHAR(255),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(32) NOT NULL,
  message_text TEXT NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'chat',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS corrections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  original_answer TEXT NOT NULL,
  corrected_answer TEXT NOT NULL,
  note TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind VARCHAR(64) NOT NULL,
  text TEXT NOT NULL,
  source VARCHAR(64) NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_edges (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_node VARCHAR(255) NOT NULL,
  relation VARCHAR(64) NOT NULL DEFAULT 'co_occurs',
  target_node VARCHAR(255) NOT NULL,
  weight INTEGER NOT NULL DEFAULT 1,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_created
  ON conversations (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_corrections_user_created
  ON corrections (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_items_user_kind_created
  ON memory_items (user_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_user_relation
  ON knowledge_edges (user_id, relation);
