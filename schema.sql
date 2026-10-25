CREATE SEQUENCE IF NOT EXISTS seq_commit_id START 1;

CREATE TABLE IF NOT EXISTS wasm_modules (
    module_name VARCHAR PRIMARY KEY,
    category VARCHAR,
    description VARCHAR,
    bytecode_size_bytes INTEGER,
    exported_functions_json VARCHAR,
    content_hash VARCHAR,
    wasm_url VARCHAR,
    last_compiled_utc VARCHAR
);

CREATE TABLE IF NOT EXISTS wasm_ledger (
    commit_id BIGINT PRIMARY KEY,
    timestamp_utc VARCHAR,
    operation VARCHAR,
    module_name VARCHAR,
    bytecode_size_bytes INTEGER,
    detail VARCHAR
);
