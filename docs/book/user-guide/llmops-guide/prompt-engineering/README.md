---
description: Simple prompt engineering with ZenML - version control, A/B testing, and dashboard visualization.
icon: edit
---

# Prompt Engineering

ZenML's prompt engineering focuses on the three things teams actually need: **simple versioning**, **A/B testing**, and **dashboard visualization**.

## Quick Start

1. **Run the example**:
   ```bash
   cd examples/prompt_engineering
   python run_simple_comparison.py
   ```

2. **Check your dashboard** to see prompt artifacts with rich visualizations

## Core Features

### Git-like Versioning
```python
prompt_v1 = Prompt(template="Answer: {question}", version="1.0")
prompt_v2 = Prompt(template="Detailed answer: {question}", version="2.0") 
```

### A/B Testing
```python
# Pipeline automatically compares versions and determines winner
result = simple_prompt_comparison()
print(f"Winner: {result['winner']}")
```

### Dashboard Integration
- Syntax-highlighted templates
- Variable tables and validation
- Version tracking across runs
- Side-by-side comparisons

## Why This Approach?

User research shows teams with millions of daily requests use **simple Git-based versioning**, not complex management systems. This approach focuses on what actually works in production.


## ZenML's Philosophy: Embrace Simplicity

Based on our research, ZenML's prompt management follows three principles:

### 1. **Prompts Are Versioned Artifacts**

```python
# Simple, clear, version-controlled
prompt = Prompt(
    template="Answer: {question}",
    version="2.0"  # Git-like versioning
)
```

Prompts integrate naturally with ZenML's artifact system. No special management layer required.

### 2. **Forward-Looking Experimentation Over Backward-Looking Management**

```python
# Focus on comparing forward
result = compare_prompts(
    prompt_a=new_prompt,
    prompt_b=current_prompt,
    test_cases=real_scenarios
)
```

Instead of complex version trees, focus on "Does this new prompt work better?"


## Documentation

* [Quick Start](quick-start.md) - Working example walkthrough
* [Understanding Prompt Management](understanding-prompt-management.md) - Research and philosophy  
* [Best Practices](best-practices.md) - Production guidance

## Example Structure

The `examples/prompt_engineering/` directory demonstrates proper organization:
- `pipelines/` - Pipeline definitions
- `steps/` - Individual step implementations
- `utils/` - Helper functions
- Clean separation of concerns

Start with the quick start example to see all features in action.