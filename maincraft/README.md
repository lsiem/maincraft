# Modpack Knowledge Engine

A local, conversational AI guide for complex Minecraft modpacks — **GregTech: New Horizons (GTNH)** and **Enigmatica** (E2E, E6, E9).

Hybrid architecture:
- **Static RAG** — ChromaDB vector index of questbooks, wiki pages, and recipe changes
- **Dynamic LLM Wiki** — Karpathy-style markdown files tracking your specific world state

## Quick Start

```bash
cd maincraft
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # only needed for GTNH wiki fallback

# Configure (optional — defaults to Ollama)
export LLM_BACKEND=ollama
export OLLAMA_CHAT_MODEL=llama3.2
export OLLAMA_EMBED_MODEL=nomic-embed-text

# Ingest all packs (downloads GitHub tarballs, parses, indexes)
python -m ingestion.chunk_and_index --all

# Skip wiki fetching if GTNH wiki API is blocked (quests still indexed)
python -m ingestion.chunk_and_index --all --skip-wiki

# Opt into slow Playwright wiki fallback
python -m ingestion.chunk_and_index --pack gtnh --wiki-playwright

# Start the CLI
python -m cli.main
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/set-pack gtnh\|e2e\|e6\|e9` | Set active modpack context |
| `/describe-world <text>` | Update player state in session wiki |
| `/reindex` | Re-run ingestion pipeline |
| Free text | Ask the guide anything |

## Project Structure

```
maincraft/
  config.py              # Pack registry, model backends, paths
  ingestion/             # Data fetchers and parsers
  agent/                 # LangGraph ReAct agent + tools
  cli/                   # Rich terminal interface
  session_wiki/          # Dynamic player state (markdown)
  data/
    raw/                 # Cached source data
    chroma/              # Vector index
```

## Data Sources

| Pack | Quest Format | Scripts | Docs |
|------|-------------|---------|------|
| GTNH | BetterQuesting tree (`DefaultQuests/`) | — | GTNH Wiki (Miraheze) |
| E2E | BetterQuesting JSON (`DefaultQuests.json`) | ZenScript `scripts/` | — |
| E6/E9 | FTB Quests SNBT (`chapters/*.snbt`) | KubeJS `server_scripts/` | Enigmatica GitBook |

## GTNH Wiki Fallback

The GTNH wiki (Miraheze) blocks non-browser API access. The fetcher tries the MediaWiki API first, then falls back to Playwright. If both fail, you can manually export pages:

1. Visit `https://wiki.gtnewhorizons.com/wiki/Special:Export`
2. Enter page names from the priority list in `config.py`
3. Save the XML to `data/raw/gtnh_wiki/export.xml`
4. Re-run ingestion — the parser will pick it up automatically.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `ollama` | `ollama` or `openai` |
| `EMBED_BACKEND` | `ollama` | `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | Chat model name |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `OPENAI_API_KEY` | — | Required if using OpenAI backend |
