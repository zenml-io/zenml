# Hierarchical Document Search Agent

A showcase for ZenML's **Dynamic Pipelines** feature, demonstrating how to combine ZenML orchestration with Pydantic AI agents.

## The Core Idea

This example splits responsibilities between two systems:

| ZenML Controls | Pydantic AI Controls |
|----------------|---------------------|
| Breadth (how many starting docs) | "Does this document answer the query?" |
| Budget/depth limits | "Should I traverse deeper?" |
| Step orchestration & DAG | "Which documents to explore next?" |
| Artifact tracking | Natural language reasoning |

The result: each `traverse_node` call appears as a **separate step** in the DAG, dynamically created at runtime based on agent decisions.

## What You'll See in the DAG

```
detect_intent
     │
     ├── [simple] → simple_search → create_report
     │
     └── [deep] → plan_search
                      │
                      ├── traverse_node (doc_1)  ─┐
                      ├── traverse_node (doc_2)   ├── Each is a separate
                      ├── traverse_node (doc_3)   │   step in the DAG!
                      └── traverse_node (doc_4)  ─┘
                              │
                              └── aggregate_results → create_report
```

## Prerequisites

- **OPENAI_API_KEY**: Required for LLM-powered search. Without it, falls back to keyword matching.
- **LLM_MODEL** (optional): The model to use for agent reasoning. Defaults to `openai:gpt-5-nano`. Example: `LLM_MODEL=openai:gpt-4o`
- **MAX_ANSWER_CHARS** (optional): Maximum characters for answer text. Defaults to `10000`. Set to `0` for unlimited.

## Sample Document Topics

The example uses a sample document graph (`data/doc_graph.json`) with content about:

- **Python** — introduction and advanced concepts
- **Quantum computing** — basics, algorithms, applications, quantum ML
- **Machine learning** — fundamentals, deep learning
- **Web development**, **data science**, **distributed systems**, **software engineering**

**Try queries that relate to these topics**, e.g.:
- "How does quantum computing relate to machine learning?"
- "What are advanced Python concepts?"
- "Compare distributed systems and software engineering"

For custom use cases, replace `doc_graph.json` with your own document hierarchy.

## Quick Start

**Important:** Run commands from within this example directory:

```bash
cd examples/hierarchical_doc_search_agent
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
# Optionally override the default model (gpt-5-nano):
# export LLM_MODEL="openai:gpt-4o"
zenml init && zenml login

# Simple query (fast keyword search)
python run.py --query "What is Python?"

# Deep query (agents traverse the document graph)
python run.py --query "How does quantum computing relate to machine learning?"

# Control breadth and depth (clamped: max_agents 1-10, max_depth 1-5)
python run.py --query "Compare ML approaches" --max-agents 5 --max-depth 3
```

---

## Understanding Dynamic Pipelines

This is the most important section. Dynamic pipelines change how you handle **Artifacts vs. Parameters**.

### 1. Parameters vs. Artifacts: When to Use `.with_options()`

In dynamic pipelines, you often mix **artifact-derived values** (outputs from upstream steps that create DAG edges) with **plain Python values** (pipeline inputs, computed values).

Use `.with_options(parameters={...})` when you want to **explicitly mark** a value as a pipeline parameter. This is especially useful when:
- The value comes from a `.load()` call (dynamically retrieved artifact data)
- You want to force parameter semantics inside loops or dynamic control flow
- You want clearer separation between DAG edges and configuration values

```python
# Explicitly mark 'query' as a parameter (not an artifact dependency)
traverse_node_step = traverse_node.with_options(
    parameters={"query": query}
)

# Now call the step - doc_id creates a DAG edge, query is a parameter
traverse_node_step(
    doc_id=seed_nodes.chunk(index=idx),  # Artifact chunk → DAG edge
    budget=budget,                        # Plain value
    visited=visited,                      # Plain value
)
```

**Note:** Simple values like `budget` and `visited` work fine without `.with_options()` — ZenML handles them as parameters automatically. The explicit form is most useful for clarity and when values originate from dynamic contexts.

### 2. The `.chunk()` vs `.load()` Pattern

When looping through artifact lists, you need two different operations:

| Method | Purpose | When to Use |
|--------|---------|-------------|
| `.chunk(index=idx)` | Creates a **DAG edge** | Pass to downstream steps |
| `.load()` | Gets the **actual value** | Make control-flow decisions |

```python
from collections import deque

# Get seed documents from plan_search step
seed_nodes = plan_search(query=query, ...)

# Build initial queue using BOTH patterns:
# Using deque for efficient O(1) popleft() instead of list.pop(0)
pending = deque(
    (seed_nodes.chunk(index=idx), max_depth, [])  # .chunk() for DAG edge
    for idx in range(len(seed_nodes.load()))  # .load() to get count
)

while pending:
    doc_id_chunk, budget, visited = pending.popleft()

    # Pass the chunk as input (creates DAG edge)
    result, traverse_to = traverse_node_step(
        doc_id=doc_id_chunk,  # This is a chunk, not a raw value
        budget=budget,
        visited=visited,
    )

    # Load values to make decisions about spawning more steps
    result_data = result.load()
    traverse_to_data = traverse_to.load()

    if not result_data["found_answer"] and result_data["budget"] > 0:
        # Cap follow-up traversals to 2 per node to limit DAG growth
        for idx in range(min(2, len(traverse_to_data))):
            # Use .chunk() again for the next iteration
            pending.append((
                traverse_to.chunk(index=idx),
                result_data["budget"],
                result_data["visited"],
            ))
```

**Key insight**: `.chunk(idx)` tells the orchestrator "Step B depends on item X from Step A's output list." `.load()` just gets the value for your Python logic.

---

## How It Works

1. **Intent Detection** — Classifies query as "simple" or "deep"
2. **Plan Search** — Finds starting documents (seed nodes)
3. **Breadth Expansion** — Creates traversal steps for each seed document
4. **Agent Decision** — Pydantic AI decides: answer found or traverse deeper?
5. **Dynamic Expansion** — If "traverse", new steps are added to the DAG
6. **Aggregate** — Combines all findings into final results

## Deploy as HTTP Service

**Important:** Run the deploy command from within this example directory (same as Quick Start).

```bash
cd examples/hierarchical_doc_search_agent
zenml pipeline deploy hierarchical_search_pipeline --name search
```

After deployment, get your invoke URL from the deployment details:

```bash
zenml pipeline deployment describe search
```

Then call the endpoint using the URL shown in the output:

```bash
curl -X POST <YOUR_INVOKE_URL> \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "How does X relate to Y?", "max_agents": 3}}'
```

## Web UI

The `ui/` directory contains a ready-to-use web interface for deployed pipelines:

- Search input with example queries
- Configurable max_agents and max_depth sliders
- Real-time metrics (search type, agents used, docs explored)
- Result cards with answers

## Project Structure

```
├── run.py                           # CLI entry point
├── requirements.txt                 # Dependencies
├── pipelines/
│   └── hierarchical_search_pipeline.py  # Dynamic pipeline logic
├── steps/
│   └── search.py                    # Step implementations + Pydantic AI agent
├── data/
│   ├── doc_graph.json               # Sample document graph
│   ├── report.css                   # CSS styles for HTML report
│   └── report_template.html         # HTML template for report artifact
└── ui/
    └── index.html                   # Web UI for deployed pipeline
```

## Further Reading

- [ZenML Dynamic Pipelines Documentation](https://docs.zenml.io)
- [Pydantic AI Documentation](https://ai.pydantic.dev)
