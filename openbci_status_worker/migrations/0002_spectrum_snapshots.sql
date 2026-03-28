CREATE TABLE IF NOT EXISTS spectrum_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  updated_at TEXT NOT NULL,
  received_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  paf_hz REAL,
  gamma_delta_ratio REAL,
  one_over_f_slope REAL,
  one_over_f_r2 REAL,
  artifact_flag INTEGER NOT NULL DEFAULT 0,
  quality TEXT,
  active_channels TEXT,
  spectrum_channels TEXT,
  spectrum_points INTEGER
);

CREATE INDEX IF NOT EXISTS idx_spectrum_snapshots_updated_at ON spectrum_snapshots(updated_at DESC);
