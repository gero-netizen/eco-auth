PRAGMA foreign_keys = ON;

CREATE TABLE work_orders (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  address TEXT NOT NULL,
  status TEXT NOT NULL,
  latitude REAL,
  longitude REAL,
  version INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  dirty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sync_operations (
  operation_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  base_version INTEGER,
  occurred_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);

CREATE INDEX sync_operations_state_idx ON sync_operations(state, occurred_at);

CREATE TABLE attachments (
  id TEXT PRIMARY KEY,
  work_order_id TEXT NOT NULL REFERENCES work_orders(id),
  category TEXT NOT NULL,
  local_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  remote_key TEXT,
  upload_state TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL
);

CREATE TABLE inventory_items (
  id TEXT PRIMARY KEY,
  sku TEXT NOT NULL,
  description TEXT NOT NULL,
  serial_number TEXT,
  quantity REAL NOT NULL,
  version INTEGER NOT NULL,
  dirty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE inventory_movements (
  id TEXT PRIMARY KEY,
  work_order_id TEXT REFERENCES work_orders(id),
  item_id TEXT NOT NULL REFERENCES inventory_items(id),
  quantity REAL NOT NULL,
  kind TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  sync_state TEXT NOT NULL DEFAULT 'pending'
);

