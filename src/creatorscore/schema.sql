-- One template, two dialects ({PK} is substituted in db.py). Timestamps are ISO-8601 UTC text.
CREATE TABLE IF NOT EXISTS creators (
  id {PK},
  handle TEXT NOT NULL,
  platform TEXT NOT NULL,
  category TEXT,
  followers BIGINT NOT NULL,
  rate_usd DOUBLE PRECISION,
  is_sample INTEGER NOT NULL DEFAULT 0,
  UNIQUE (platform, handle)
);
CREATE TABLE IF NOT EXISTS creator_posts (
  id {PK},
  creator_id BIGINT NOT NULL REFERENCES creators(id),
  posted_at TEXT NOT NULL,
  views BIGINT NOT NULL,
  likes BIGINT NOT NULL,
  comments BIGINT NOT NULL,
  shares BIGINT NOT NULL DEFAULT 0,
  dup_comment_ratio DOUBLE PRECISION,
  UNIQUE (creator_id, posted_at)
);
CREATE TABLE IF NOT EXISTS creator_followers (
  creator_id BIGINT NOT NULL REFERENCES creators(id),
  captured_at TEXT NOT NULL,
  followers BIGINT NOT NULL,
  PRIMARY KEY (creator_id, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_cposts_creator ON creator_posts (creator_id, posted_at);
