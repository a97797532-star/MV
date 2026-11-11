PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS experiments (
 run_id TEXT PRIMARY KEY,
 model TEXT NOT NULL,
 model_version TEXT NOT NULL,
 source_commit TEXT,
 config_json TEXT NOT NULL,
 dataset_manifest_sha256 TEXT NOT NULL,
 split_manifest_sha256 TEXT NOT NULL,
 seed INTEGER NOT NULL,
 environment_lock_sha256 TEXT NOT NULL,
 device TEXT NOT NULL,
 started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
 run_id TEXT NOT NULL REFERENCES experiments(run_id),
 scope TEXT NOT NULL CHECK(scope IN ('product','location','cost')),
 name TEXT NOT NULL,
 value REAL,
 unit TEXT NOT NULL,
 category TEXT NOT NULL DEFAULT 'all',
 camera TEXT NOT NULL DEFAULT 'all',
 region TEXT NOT NULL DEFAULT 'all',
 PRIMARY KEY(run_id,scope,name,category,camera,region)
);
CREATE TABLE IF NOT EXISTS artifacts (
 run_id TEXT NOT NULL REFERENCES experiments(run_id),
 kind TEXT NOT NULL,
 relative_path TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 PRIMARY KEY(run_id, relative_path)
);
