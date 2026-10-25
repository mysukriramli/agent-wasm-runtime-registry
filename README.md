```markdown
# ⚙️ Agent Wasm Runtime Registry

An autonomous execution plane running entirely on GitHub Actions. It compiles, verifies, and hosts sandboxed WebAssembly (Wasm) micro-modules that allow autonomous agents to offload deterministic mathematical calculations, risk scoring, and text heuristics with zero token spend and microsecond latency.

## Impact & Token Savings
- **Zero Token Hallucinations**: Math executes inside a sandboxed Wasm runtime rather than natural language inference.
- **Micro-Binaries**: Modules are compiled from WebAssembly Text Format (`.wat`) to binaries under 200 bytes.

## Machine Feeds
- [`v1/modules.json`](public/v1/modules.json) (Module index & signatures)
- [`llms.txt`](public/llms.txt) (Token-efficient LLM digest)
- `modules.parquet` (Columnar database snapshot)

## Architecture
- **Compiler**: `wat2wasm` (WebAssembly Binary Toolkit - WABT)
- **Database**: DuckDB + Parquet
- **Ledger**: Append-only Git-committed JSONL in `/data/history`
- **Edge CDN**: GitHub Pages (Fastly CDN)