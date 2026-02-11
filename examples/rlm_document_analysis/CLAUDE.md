# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A ZenML example demonstrating **Dynamic Pipelines** applied to the **Reasoning Language Model (RLM)** pattern. It analyzes an email corpus (Enron dataset) by dynamically decomposing a research query into parallel chunk analyses, each running a constrained multi-step reasoning loop, then synthesizing findings into an HTML report.

This lives inside the larger ZenML monorepo at `examples/rlm_document_analysis/`. See the root `CLAUDE.md` for ZenML-wide conventions.

## Commands

```bash
# Install dependencies (run from this directory)
pip install -r requirements.txt

# Run with bundled 60-email sample
python run.py

# Custom query
python run.py --query "What concerns did Vince Kaminski raise about risk?"

# Control parallelism and depth
python run.py --query "Trace the Raptor vehicle timeline" --max-chunks 5 --max-iterations 8

# Run without LLM (keyword fallback mode)
unset OPENAI_API_KEY
python run.py --query "California trading strategies"

# Download full Enron dataset from HuggingFace (requires `pip install datasets`)
python setup_data.py                  # First 1000 emails
python setup_data.py --limit 5000     # First 5000
python setup_data.py --limit 0        # All 517K (warning: large)
python run.py --source data/emails.json --query "your query"
```

## Required Environment Variables

- **`OPENAI_API_KEY`**: Required for LLM-powered analysis. Without it, every step degrades to keyword matching (functional but low-confidence).
- **`LLM_MODEL`** (optional): Defaults to `gpt-4o-mini`. Override with e.g. `LLM_MODEL=gpt-4o`.

## Architecture

### Pipeline DAG (shape determined at runtime)

```
load_documents → plan_decomposition → [process_chunk, process_chunk_2, ..N] → aggregate_results
```

The number of `process_chunk` steps is decided by the LLM at runtime based on the query and corpus summary. ZenML auto-names repeated invocations (`process_chunk`, `process_chunk_2`, etc.). This is ZenML's **dynamic pipeline** feature (`@pipeline(dynamic=True)`).

### Module layout

| Module | Role |
|--------|------|
| `run.py` | CLI entry point — parses args and calls the pipeline |
| `pipelines/rlm_pipeline.py` | Pipeline definition with dynamic fan-out loop + deployment settings |
| `steps/loading.py` | Loads JSON emails, builds corpus summary |
| `steps/decomposition.py` | LLM plans chunk boundaries (or even-split fallback) |
| `steps/processing.py` | **Core RLM loop** per chunk: preview → plan → search → reflect → (repeat or summarize) |
| `steps/aggregation.py` | Synthesizes chunk findings + trajectories into HTML report (external template) |
| `utils/llm.py` | OpenAI wrapper with retry, exponential backoff, and graceful fallback |
| `utils/tools.py` | Typed search tools (grep, sender, recipient, date, count) |
| `data/report.css` | External report stylesheet (ZenML design system) |
| `data/report_template.html` | External HTML report template with `str.format()` placeholders |
| `ui/index.html` | Deployable static dashboard for ZenML pipeline deployment |
| `setup_data.py` | Downloads full Enron dataset from HuggingFace |

### Key dynamic pipeline patterns

The fan-out in `rlm_pipeline.py` uses two ZenML-specific APIs that are easy to confuse:

- **`.load()`** — Materializes the artifact value for control-flow decisions (e.g. `len(chunk_specs.load())` to determine loop count)
- **`.chunk(index=idx)`** — Creates a DAG edge without materializing (e.g. `chunk_specs.chunk(index=idx)` passed to downstream steps)
- **`.with_options(parameters=...)`** — Binds values as step parameters (not artifact dependencies)

### Iterative RLM pattern

The LLM cannot execute arbitrary code. Instead, `process_chunk` runs a bounded iterative loop:

1. **Plan** — LLM selects from 5 typed tools (grep, sender, recipient, date, count)
2. **Search** — Tools execute programmatically
3. **Reflect** — LLM evaluates: "Do I have enough evidence, or should I search differently?"
4. If not sufficient, loop back to Plan with refined strategy
5. **Summarize** — Final synthesis of all gathered evidence

Each plan+reflect iteration costs 2 LLM calls; the final summarize costs 1. The `max_iterations` parameter controls the total LLM call budget per chunk. Every action is logged to a trajectory artifact for observability. Trajectories are rendered as collapsible JSON blocks in the HTML report.

### Report generation

The HTML report uses external assets loaded at runtime (mirrors the hierarchical_doc_search_agent pattern):

- `data/report.css` — ZenML design system CSS
- `data/report_template.html` — HTML template with `str.format()` placeholders

Asset loading uses `_load_text_asset()` with three fallback paths: relative to `steps/`, Docker `/app/`, and plain relative. The template uses these placeholders: `{css}`, `{query_safe}`, `{chunk_count}`, `{confidence_safe}`, `{confidence_class}`, `{summary_safe}`, `{key_findings_html}`, `{evidence_gaps_html}`, `{chunk_cards_html}`.

**Important**: The template file must not contain literal `{` or `}` outside placeholders (Python `str.format()` would interpret them). All CSS goes in `report.css` injected via `{css}`.

### Deployment

The pipeline includes `DeploymentSettings` (app_title, app_description, dashboard_files_path="ui") for ZenML deployment. The `ui/index.html` provides a static dashboard with Jinja-injected globals (`INVOKE_URL`, `AUTH_ENABLED`) and controls for query, max_chunks, and max_iterations.

### Dual-mode operation

Every LLM-dependent step has a fallback path when `OPENAI_API_KEY` is unset:
- `plan_decomposition` → even-split chunks
- `process_chunk` → keyword matching
- `aggregate_results` → concatenation of findings

This means the pipeline always runs, just with lower-quality results.

## Budget Controls

| Layer | Parameter | Default | Range | Controls |
|-------|-----------|---------|-------|----------|
| Pipeline | `max_chunks` | 4 | 1-10 | DAG width (number of parallel process_chunk steps) |
| Step | `max_iterations` | 6 | 2-12 | Max LLM calls per chunk |

Both are clamped in `rlm_pipeline.py` to prevent resource exhaustion.

## Data Format

Emails are JSON arrays of objects with fields: `from`, `to`, `cc`, `date`, `subject`, `body`. The bundled sample at `data/sample_emails.json` contains 60 synthetic Enron-style emails. Downloaded datasets go to `data/emails.json` (gitignored).
