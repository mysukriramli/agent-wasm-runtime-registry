import os
import re
import glob
import json
import shutil
import hashlib
import duckdb
import subprocess
from datetime import datetime, timezone

DB_FILE = "data/wasm_registry.db"
HISTORY_DIR = "data/history"
MODULES_SRC_DIR = "modules"
EXPORT_DIR = "public"
API_DIR = os.path.join(EXPORT_DIR, "v1")
WASM_OUTPUT_DIR = os.path.join(EXPORT_DIR, "wasm")

MODULE_METADATA = {
    "risk_scorer": {
        "category": "threat_assessment",
        "description": "Deterministic composite CVSS + EPSS risk scoring math."
    },
    "token_estimator": {
        "category": "nlp_utility",
        "description": "Zero-overhead token count estimation based on byte length and word count."
    },
    "geo_distance": {
        "category": "spatial_math",
        "description": "Microsecond planar coordinate distance calculation."
    }
}

def compute_hash(binary_data: bytes) -> str:
    return hashlib.sha256(binary_data).hexdigest()

def extract_exports(wat_path: str) -> list[str]:
    exports = []
    try:
        with open(wat_path, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r'\(export\s+"([^"]+)"\)', content)
            exports = list(set(matches))
    except Exception:
        pass
    return exports

def compile_wat_modules():
    compiled_modules = []
    os.makedirs(WASM_OUTPUT_DIR, exist_ok=True)
    
    wat_files = glob.glob(os.path.join(MODULES_SRC_DIR, "*.wat"))
    for wat_file in sorted(wat_files):
        mod_name = os.path.splitext(os.path.basename(wat_file))[0]
        wasm_file = os.path.join(WASM_OUTPUT_DIR, f"{mod_name}.wasm")
        
        # Compile via wat2wasm (from wabt toolchain)
        cmd = ["wat2wasm", wat_file, "-o", wasm_file]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            with open(wasm_file, "rb") as f:
                bytecode = f.read()
                
            exports = extract_exports(wat_file)
            compiled_modules.append({
                "module_name": mod_name,
                "category": MODULE_METADATA.get(mod_name, {}).get("category", "general_compute"),
                "description": MODULE_METADATA.get(mod_name, {}).get("description", "Deterministic Wasm micro-kernel"),
                "bytecode_size": len(bytecode),
                "exports": exports,
                "content_hash": compute_hash(bytecode),
                "wasm_url": f"wasm/{mod_name}.wasm"
            })
        except Exception as e:
            print(f"Compilation error on {wat_file}: {e}")
            
    return compiled_modules

def build_static_api(conn):
    os.makedirs(API_DIR, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()
    
    cur = conn.execute("SELECT module_name, category, description, bytecode_size_bytes, exported_functions_json, content_hash, wasm_url, last_compiled_utc FROM wasm_modules ORDER BY module_name ASC")
    cols = [desc[0] for desc in cur.description]
    modules = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        d["exported_functions"] = json.loads(d["exported_functions_json"])
        del d["exported_functions_json"]
        modules.append(d)

    with open(os.path.join(API_DIR, "modules.json"), "w", encoding="utf-8") as f:
        json.dump({"metadata": {"updated_at": now_iso, "count": len(modules)}, "modules": modules}, f, indent=2)

    lines = [
        "# Agent Wasm Runtime Registry",
        f"> Last Sync: {now_iso} UTC",
        "> Optimization: Sandboxed WebAssembly micro-kernels offloading deterministic math and transformations from LLMs.",
        "",
        "## Available Pre-Compiled Wasm Micro-Kernels"
    ]
    for m in modules:
        exports_str = ", ".join([f"`{e}()`" for e in m["exported_functions"]])
        lines.append(f"- **{m['module_name']}** ({m['category']} | {m['bytecode_size_bytes']} bytes): {m['description']}\n  Exports: {exports_str} | Binary: `{m['wasm_url']}`")

    with open(os.path.join(EXPORT_DIR, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    html = f"""<!DOCTYPE html><html><head><title>Agent Wasm Runtime Registry</title></head>
    <body style='font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;line-height:1.6;padding:0 1rem;'>
    <h1>⚙️ Agent Wasm Runtime Registry</h1>
    <p>Pre-compiled, sandboxed WebAssembly micro-kernels executing deterministic agent compute without LLM tokens.</p>
    <h3>Machine Feeds</h3>
    <ul>
      <li><a href='v1/modules.json'>/v1/modules.json</a> (Module Catalog &amp; Export Signatures)</li>
      <li><a href='llms.txt'>llms.txt</a> (Token-Efficient Digest)</li>
      <li><a href='modules.parquet'>modules.parquet</a> (Columnar Parquet Snapshot)</li>
    </ul>
    <h3>Compiled Micro-Kernels</h3>
    <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%;text-align:left;">
      <tr><th>Module</th><th>Category</th><th>Size</th><th>Exports</th><th>Binary</th></tr>
      {"".join([f"<tr><td><strong>{m['module_name']}</strong></td><td>{m['category']}</td><td>{m['bytecode_size_bytes']} B</td><td><code>{', '.join(m['exported_functions'])}</code></td><td><a href='{m['wasm_url']}'>Download .wasm</a></td></tr>" for m in modules])}
    </table>
    </body></html>"""
    with open(os.path.join(EXPORT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def run():
    os.makedirs("data", exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    conn = duckdb.connect(DB_FILE)
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.execute(f.read())

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    date_str = now.strftime("%Y-%m-%d")
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    month_dir = os.path.join(HISTORY_DIR, year_str, month_str)
    os.makedirs(month_dir, exist_ok=True)
    daily_history_file = os.path.join(month_dir, f"{date_str}.jsonl")

    modules = compile_wat_modules()

    conn.execute("BEGIN TRANSACTION")

    for mod in modules:
        m_name = mod["module_name"]
        cat = mod["category"]
        desc = mod["description"].replace("'", "''")
        size = mod["bytecode_size"]
        exports_json = json.dumps(mod["exports"])
        h = mod["content_hash"]
        url = mod["wasm_url"]

        existing = conn.execute(f"SELECT content_hash FROM wasm_modules WHERE module_name = '{m_name}'").fetchone()

        if not existing:
            conn.execute(f"""
                INSERT INTO wasm_modules (
                    module_name, category, description, bytecode_size_bytes,
                    exported_functions_json, content_hash, wasm_url, last_compiled_utc
                ) VALUES (
                    '{m_name}', '{cat}', '{desc}', {size},
                    '{exports_json}', '{h}', '{url}', '{now_iso}'
                )
            """)

            commit_id = conn.execute("SELECT nextval('seq_commit_id')").fetchone()[0]
            conn.execute(f"""
                INSERT INTO wasm_ledger (commit_id, timestamp_utc, operation, module_name, bytecode_size_bytes, detail)
                VALUES ({commit_id}, '{now_iso}', 'COMPILE_MODULE', '{m_name}', {size}, 'Initial wasm binary compiled')
            """)

            entry = {
                "commit_id": commit_id, "timestamp_utc": now_iso, "operation": "COMPILE_MODULE",
                "module_name": m_name, "bytecode_size_bytes": size, "content_hash": h
            }
            with open(daily_history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        elif existing[0] != h:
            conn.execute(f"""
                UPDATE wasm_modules SET
                    category = '{cat}',
                    description = '{desc}',
                    bytecode_size_bytes = {size},
                    exported_functions_json = '{exports_json}',
                    content_hash = '{h}',
                    wasm_url = '{url}',
                    last_compiled_utc = '{now_iso}'
                WHERE module_name = '{m_name}'
            """)

            commit_id = conn.execute("SELECT nextval('seq_commit_id')").fetchone()[0]
            conn.execute(f"""
                INSERT INTO wasm_ledger (commit_id, timestamp_utc, operation, module_name, bytecode_size_bytes, detail)
                VALUES ({commit_id}, '{now_iso}', 'MODULE_DRIFT', '{m_name}', {size}, 'Bytecode content hash updated')
            """)

            entry = {
                "commit_id": commit_id, "timestamp_utc": now_iso, "operation": "MODULE_DRIFT",
                "module_name": m_name, "bytecode_size_bytes": size, "content_hash": h
            }
            with open(daily_history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    conn.execute("COMMIT")

    conn.execute(f"COPY (SELECT module_name, category, description, bytecode_size_bytes, content_hash, wasm_url, last_compiled_utc FROM wasm_modules) TO '{EXPORT_DIR}/modules.parquet' (FORMAT PARQUET)")
    build_static_api(conn)
    conn.close()

if __name__ == "__main__":
    run()
