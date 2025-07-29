# Simplified Prompt Management in ZenML

This directory contains examples of ZenML's simplified prompt management system, focused on the three core features users actually want:

1. **Prompt Versioning** - Git-like versioning for prompts
2. **Dashboard Visualization** - See prompt versions in pipeline runs
3. **Easy A/B Comparison** - Compare different prompts with simple metrics

## What's New (Simplified)

- **Prompts are versioned artifacts** - Each prompt has a `version` field
- **Rich dashboard visualization** - HTML/Markdown views of prompts in the dashboard
- **Simple comparison utilities** - Compare prompts without complex infrastructure

## Quick Start

```python
from zenml import pipeline, step
from zenml.prompts import Prompt

# 1. Create versioned prompts
prompt_v1 = Prompt(
    template="Answer concisely: {question}",
    version="1.0.0"
)

prompt_v2 = Prompt(
    template="Provide detailed answer: {question}", 
    version="2.0.0"
)

# 2. Use in pipelines - versions show in dashboard
@pipeline
def my_pipeline(prompt: Prompt):
    result = llm_step(prompt)
    return result

# 3. Compare prompts easily
from zenml.prompts import compare_prompts

result = compare_prompts(
    prompt_a=prompt_v1,
    prompt_b=prompt_v2,
    test_cases=[{"question": "What is ML?"}],
    llm_function=my_llm_call,
    metric_functions={"length": lambda r, t: len(r[0])}
)
```

## Examples

### 1. Simple Comparison Pipeline (`simple_comparison_example.py`)

Shows how to:
- Create multiple prompt versions
- Test each version in a pipeline
- Compare results to pick a winner
- View everything in the dashboard

### 2. Basic Prompt Pipeline (`simple_pipeline.py`)

Shows how to:
- Create a versioned prompt
- Use it with an LLM
- Track results in ZenML

## Dashboard Features

When you run these pipelines, the ZenML dashboard will show:

- **Prompt versions** in the artifact view
- **Rich HTML visualization** with syntax highlighting
- **Variable tables** showing required inputs
- **Sample outputs** when variables are provided
- **Version comparison** across runs

## Key Differences from Complex Implementation

❌ **What we removed:**
- Server-side prompt template management
- Database schemas and migrations
- Complex diff utilities
- REST APIs for CRUD operations
- 50+ files of infrastructure

✅ **What we kept:**
- Simple Prompt class with version field
- Dashboard visualization
- Basic comparison utilities
- Git-like versioning approach

## Best Practices

1. **Use Git for long-term storage** - Prompts are code
2. **Version bumps for changes** - Update version when modifying prompts
3. **A/B test in production** - Use simple comparison utilities
4. **Focus on metrics** - Let your metrics drive decisions

## Integration with Existing Code

```python
# Your existing pipeline
@pipeline
def existing_pipeline(data):
    processed = process_step(data)
    return processed

# Add prompt comparison
prompt_a = Prompt(template="...", version="1.0")
prompt_b = Prompt(template="...", version="2.0")

# Run pipeline with each prompt
run_a = existing_pipeline(data=data, prompt=prompt_a)
run_b = existing_pipeline(data=data, prompt=prompt_b)

# Compare in dashboard!
```

## Why This Approach?

Based on user research:
- Teams already use Git for versioning
- Complex prompt management is overengineering
- Forward-looking A/B testing > backward-looking versioning
- Simple is better

> "There was not one time where someone was like, hey man, I feel like the previous prompt was working so much better" - Production team with 2-6M requests/day

This implementation respects that insight by focusing on moving forward with experiments, not complex version management.