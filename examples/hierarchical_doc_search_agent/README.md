# Hierarchical Document Search Agent

**ZenML orchestration + Pydantic AI agents** - each controls what it's best at.

## The Pattern

```
ZenML controls:           Pydantic AI controls:
├── Fan-out (spawn N)     ├── "Should I traverse deeper?"
├── Budget limits         ├── "Does this answer the query?"
├── Step orchestration    └── "Which docs to explore next?"
└── DAG visualization
```

## What You'll See in the DAG

```
detect_intent
     │
     ├── [simple] → simple_search → create_report
     │
     └── [deep] → plan_search
                      │
                      ├── traverse_node (doc_1)  ─┐
                      ├── traverse_node (doc_2)   ├── Each appears as
                      ├── traverse_node (doc_3)   │   separate step!
                      └── traverse_node (doc_4)  ─┘
                              │
                              └── aggregate_results → create_report
```

## Prerequisites

- **OPENAI_API_KEY**: Required for full LLM-powered search. Without it, the example falls back to keyword matching.
- **LLM_MODEL** (optional): Override the default model (`openai:gpt-4o-mini`). Example: `LLM_MODEL=openai:gpt-4o`

## Quick Start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"  # Required for LLM-powered search
zenml init && zenml login

# Simple query (fast path)
python run.py --query "What is Python?"

# Deep query (agents traverse documents)
python run.py --query "How does quantum computing relate to machine learning?"

# Control fan-out
python run.py --query "Compare ML approaches" --max-agents 5 --max-depth 3
```

## How It Works

1. **Intent Detection**: Simple vs deep search
2. **Plan Search**: Find starting documents
3. **Fan-out**: Spawn N traversal agents (each is a ZenML step)
4. **Pydantic AI Decision**: Each agent decides - answer found or traverse deeper?
5. **Follow-up**: If agent says "traverse", spawn more steps
6. **Aggregate**: Combine all findings

```python
# Pydantic AI makes decisions
traversal_agent = Agent("openai:gpt-4o-mini", output_type=TraversalDecision)

@step
def traverse_node(query, doc_id, budget, visited):
    # Pydantic AI decides: answer or traverse?
    decision = traversal_agent.run_sync(prompt)
    return {"found_answer": decision.has_answer, "traverse_to": decision.traverse_to}

# ZenML controls orchestration
for doc_id in seeds:
    result = traverse_node(...)  # Each call = separate DAG node
    for next_doc in result.load()["traverse_to"]:
        traverse_node(...)  # More DAG nodes spawned dynamically
```

## Deploy

```bash
zenml pipeline deploy pipelines.hierarchical_search_pipeline.hierarchical_search_pipeline --name search

curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "How does X relate to Y?", "max_agents": 3}}'
```

## Web UI

A Jinja2-templated HTML UI is included for deployed pipelines:

```
ui/index.html
```

Features:
- Search input with example queries
- Configurable max_agents and max_depth
- Real-time metrics (search type, agents used, docs explored)
- Result cards with answers

The UI automatically connects to your deployed pipeline endpoint.

## Files

- `pipelines/hierarchical_search_pipeline.py` - Pipeline orchestration logic
- `steps/search.py` - All step implementations + Pydantic AI agent
- `data/doc_graph.json` - Sample documents with relationships
- `ui/index.html` - Web UI for deployed pipeline
- `run.py` - CLI
