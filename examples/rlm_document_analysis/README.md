# RLM Document Analysis

A showcase for ZenML's **Dynamic Pipelines** applied to the **Recursive Language Model (RLM)** pattern — analyzing a large email corpus by dynamically decomposing it into parallel chunks, each running a constrained multi-step reasoning loop.

## The Core Idea

| ZenML Controls | Self-Rolled RLM Controls |
|----------------|--------------------------|
| How many chunks (DAG width) | "What should I search for in this chunk?" |
| Budget limits per chunk | "Is this email relevant to the query?" |
| Step orchestration & DAG | Iterative reasoning (preview → plan → search → reflect → repeat) |
| Artifact tracking & trajectory | Tool selection and evidence extraction |

The result: each `process_chunk` call is a **separate step** in the DAG, dynamically created at runtime based on how the LLM decomposes the query.

## What You'll See in the DAG

```
load_documents
     │
plan_decomposition
     │
     ├── process_chunk    ─┐
     ├── process_chunk_2   │  Dynamic fan-out
     ├── process_chunk_3   │  (number determined at runtime)
     └── process_chunk_N  ─┘
            │
       aggregate_results → report
```

Each `process_chunk` step runs an **iterative RLM reasoning loop**, bounded by the `max_iterations` LLM-call budget:

1. **Preview** — Examine the chunk (email count, date range, senders)
2. **Plan** — LLM decides which search tools to use (1 LLM call)
3. **Search** — Execute programmatic tools (grep, filter by sender/date/recipient)
4. **Reflect** — LLM evaluates: "Do I have enough evidence, or should I search differently?" (1 LLM call)
   - If not sufficient → loop back to Plan with refined strategy
   - If sufficient → proceed to Summarize
5. **Summarize** — LLM produces a final structured finding with evidence (1 LLM call)

Each plan+reflect iteration costs 2 LLM calls; the final summarize costs 1. So `max_iterations=6` allows up to 2 full search rounds plus the final synthesis.

Every action is logged to a **trajectory artifact** for full observability. Trajectories are surfaced as collapsible JSON sections in the per-chunk cards of the HTML report.

## Prerequisites

- **OPENAI_API_KEY**: Required for LLM-powered analysis. Without it, falls back to keyword matching.
- **LLM_MODEL** (optional): Model to use. Defaults to `gpt-4o-mini`. Example: `LLM_MODEL=gpt-4o`

## Dataset

The example includes a **bundled sample** of 60 synthetic Enron-style emails spanning 1999-2001, covering the major storylines (California energy trading, SPE structures, financial reporting, corporate collapse).

**Try these queries:**
- "What financial irregularities or concerns are discussed?"
- "Trace the California energy trading strategies and their risks"
- "What warnings were raised about the Raptor and LJM structures?"
- "How did leadership communicate with employees as the crisis unfolded?"

### Full Dataset

To use the real Enron corpus (517K emails):

```bash
pip install datasets
python setup_data.py                  # First 1000 emails
python setup_data.py --limit 5000     # First 5000
python setup_data.py --limit 0        # All 517K (warning: large)

python run.py --source data/emails.json --query "your query"
```

The full dataset is sourced from [corbt/enron-emails](https://huggingface.co/datasets/corbt/enron-emails) on Hugging Face.

## Quick Start

Run commands from within this example directory:

```bash
cd examples/rlm_document_analysis
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
zenml init && zenml login

# Default query with sample data
python run.py

# Custom query
python run.py --query "What concerns did Vince Kaminski raise about risk?"

# Control chunking
python run.py --query "Trace the Raptor vehicle timeline" --max-chunks 5

# Without API key (keyword fallback mode)
unset OPENAI_API_KEY
python run.py --query "California trading strategies"
```

## Understanding the RLM Pattern

### What is an RLM?

A **Recursive Language Model** uses an iterative loop where an LLM interacts with tools to analyze data it can't fit in a single context window. Instead of stuffing everything into one prompt, the RLM:

1. Previews a manageable chunk
2. Plans what to search for
3. Executes searches with typed tools
4. **Reflects** on whether it has enough evidence
5. Iterates (back to step 2) or summarizes findings

The key differentiator from simple tool-calling is the **reflect step** — the model explicitly reasons about whether its strategy is working and adapts. This is what makes it "recursive": the model can refine its approach based on what it's found so far.

This example implements a **constrained RLM** — the LLM can't execute arbitrary code. Instead, it selects from a fixed set of typed search tools, which are executed programmatically. This trades generality for production safety and observability.

### Self-Rolled vs. Framework

This example uses a self-rolled RLM (structured LLM calls + typed tools) rather than a framework like DSPy. Trade-offs:

| Self-Rolled (this example) | Framework (e.g. DSPy) |
|---------------------------|----------------------|
| Full control over the loop | Optimized prompts via compilation |
| Easy to debug and observe | Automatic prompt tuning |
| Minimal dependencies | Richer tool abstractions |
| Production-safe (no code exec) | More flexible tool use |

For production pipelines where observability and safety matter, self-rolled gives you complete control. For research where you want to optimize prompt quality, frameworks like DSPy add value.

### Dynamic Pipelines: Key Patterns

**`.chunk()` vs `.load()`** — When looping through artifact lists:

| Method | Purpose | When to Use |
|--------|---------|-------------|
| `.chunk(index=idx)` | Creates a **DAG edge** | Pass to downstream steps |
| `.load()` | Gets the **actual value** | Make control-flow decisions |

```python
chunk_specs = plan_decomposition(doc_summary=doc_summary, ...)

# .load() to determine loop count, .chunk() to create DAG edges
for idx in range(len(chunk_specs.load())):
    result, trajectory = process_step(
        documents=documents,
        chunk_spec=chunk_specs.chunk(index=idx),  # DAG edge
    )
```

**`.with_options(parameters=...)`** — Bind values as parameters (not artifact dependencies):

```python
process_step = process_chunk.with_options(
    parameters={"query": query, "max_iterations": max_iterations}
)
```

## Budget Control

| Layer | Control | Default | Limits |
|-------|---------|---------|--------|
| Pipeline | `max_chunks` | 4 | DAG width (1-10) |
| Step | `max_iterations` | 6 | LLM calls per chunk (2-12) |

## Deployment

The pipeline includes `DeploymentSettings` for ZenML deployment with a static UI dashboard:

```bash
zenml deploy --name rlm-analysis
```

The deployed service serves `ui/index.html` with controls for query, max chunks, and max iterations, and renders the HTML report artifact in an embedded iframe.

## Project Structure

```
├── run.py                          # CLI entry point
├── setup_data.py                   # Download full Enron dataset from HF
├── requirements.txt                # Dependencies
├── pipelines/
│   └── rlm_pipeline.py            # Dynamic pipeline with fan-out + deployment settings
├── steps/
│   ├── loading.py                  # Load emails + build corpus summary
│   ├── decomposition.py           # LLM plans chunk boundaries
│   ├── processing.py              # RLM-style multi-step analysis per chunk
│   └── aggregation.py             # Synthesize findings + HTML report (external template)
├── utils/
│   ├── llm.py                     # OpenAI wrapper with retry + fallback
│   └── tools.py                   # Typed search tools (grep, filter, etc.)
├── data/
│   ├── sample_emails.json          # Bundled 60-email Enron sample
│   ├── report.css                  # External report stylesheet (ZenML design system)
│   └── report_template.html        # External HTML report template
└── ui/
    └── index.html                  # Deployable static dashboard
```

## Further Reading

- [ZenML Dynamic Pipelines Documentation](https://docs.zenml.io/concepts/steps_and_pipelines/dynamic_pipelines)
- [Recursive Language Models Paper (Zhang et al., 2025)](https://arxiv.org/abs/2512.24601)
- [Enron Email Dataset (Hugging Face)](https://huggingface.co/datasets/corbt/enron-emails)
