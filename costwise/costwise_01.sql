-- costwise_01.sql — migration inicial
-- Rodar no Supabase: SQL Editor → New Query → colar e executar

CREATE TABLE IF NOT EXISTS costwise_licenses (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key             TEXT UNIQUE NOT NULL,
  email           TEXT,
  plan            TEXT DEFAULT 'lifetime',
  gumroad_sale_id TEXT,
  activated_at    TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS costwise_pings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  install_id      TEXT NOT NULL,
  version         TEXT,
  days_remaining  INT,
  is_pro          BOOLEAN,
  platform        TEXT,
  project_count   INT,
  tokens_range    TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_licenses_key        ON costwise_licenses(key);
CREATE INDEX IF NOT EXISTS idx_pings_install_id    ON costwise_pings(install_id);
CREATE INDEX IF NOT EXISTS idx_pings_created_at    ON costwise_pings(created_at);
