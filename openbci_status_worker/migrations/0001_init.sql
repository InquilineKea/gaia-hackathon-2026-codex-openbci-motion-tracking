CREATE TABLE IF NOT EXISTS eeg_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  updated_at TEXT NOT NULL,
  received_at TEXT NOT NULL,
  status_text TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  paf_hz REAL,
  alpha_theta_ratio REAL,
  gamma_delta_ratio REAL,
  one_over_f_slope REAL,
  one_over_f_r2 REAL,
  artifact_flag INTEGER NOT NULL DEFAULT 0,
  quality TEXT,
  active_channels TEXT,
  samples INTEGER,
  fs_hz REAL
);

CREATE INDEX IF NOT EXISTS idx_eeg_snapshots_updated_at ON eeg_snapshots(updated_at DESC);
