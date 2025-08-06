---
description: Comprehensive prompt engineering with ZenML - automatic versioning, structured output schemas, few-shot learning, response tracking, and rich dashboard visualization.
icon: edit
---

# Prompt Engineering

ZenML's prompt engineering provides both **simple artifact versioning** and **advanced LLM capabilities**: **automatic versioning**, **GitHub-style comparisons**, **dashboard visualization**, **structured output schemas**, **few-shot learning**, and **comprehensive response tracking**.

## Quick Start

1. **Run the example**:
   ```bash
   cd examples/prompt_engineering
   python demo_diff.py
   ```

2. **Check your dashboard** to see prompt artifacts with rich visualizations

## Core Features

### Automatic Versioning
```python
prompt_v1 = Prompt(template="Answer: {question}")
prompt_v2 = Prompt(template="Detailed answer: {question}")
# ZenML automatically versions these as artifacts: version 1, 2, 3...
```

### GitHub-Style Diff Comparison
```python
# Built-in diff functionality
diff_result = prompt_v1.diff(prompt_v2)
print(diff_result["template_diff"]["unified_diff"])

# Console output with colors
from zenml.prompts import format_diff_for_console
colored_diff = format_diff_for_console(diff_result["template_diff"])
```

### A/B Testing
```python
# Compare actual outputs from different prompts
from zenml.prompts import compare_text_outputs
comparison = compare_text_outputs(v1_outputs, v2_outputs)
print(f"Similarity: {comparison['aggregate_stats']['average_similarity']:.1%}")
```

### Enhanced LLM Features
```python
from schemas.my_schema import OutputSchema

# Structured output with schema validation
prompt = Prompt(
    template="Extract data: {document}",
    output_schema=OutputSchema.model_json_schema(),
    examples=[{
        "input": {"document": "Invoice #123 for $100"},
        "output": {"number": "123", "amount": 100}
    }]
)
```

### Response Tracking
```python
from zenml.prompts import PromptResponse

# Comprehensive LLM response artifacts
response = PromptResponse(
    content="Extracted data here",
    parsed_output={"structured": "data"},
    total_cost=0.002,
    quality_score=0.94
)
```

### Dashboard Integration
- Syntax-highlighted templates with HTML diffs
- Variable tables and validation
- **Schema visualization** with JSON schema display
- **Few-shot examples** with input/output pairs
- **Response tracking** with cost, quality, and performance metrics
- Automatic version tracking via ZenML artifacts
- GitHub-style side-by-side comparisons

## Why This Approach?

User research shows teams with millions of daily requests use **simple artifact-based versioning**, not complex management systems. ZenML leverages its existing artifact infrastructure for automatic versioning.

## ZenML's Philosophy: Embrace Simplicity

Based on our research, ZenML's prompt management follows three principles:

### 1. **Prompts Are Auto-Versioned Artifacts**

```python
# Simple, clear, automatically versioned
prompt = Prompt(template="Answer: {question}")
# ZenML handles versioning automatically when used in pipelines
```

Prompts integrate naturally with ZenML's artifact system. No manual version management required.

### 2. **Built-in Diff Functionality**

```python
# Core ZenML functionality for comparison
diff_result = prompt1.diff(prompt2)
# Get unified diffs, HTML diffs, statistics, and more
```

GitHub-style diffs are built into the core Prompt class, available everywhere.

### 3. **Forward-Looking Experimentation**

```python
# Focus on comparing what works better
output_comparison = compare_text_outputs(v1_results, v2_results)
```

Instead of complex version trees, focus on "Does this new prompt work better?"


## Documentation

* [Quick Start](quick-start.md) - Working example walkthrough
* [Understanding Prompt Management](understanding-prompt-management.md) - Research and philosophy  
* [Best Practices](best-practices.md) - Production guidance including **artifact tracing** and **prompt-response relationships**

## Example Structure

The `examples/prompt_engineering/` directory demonstrates proper organization:
- `pipelines/` - Pipeline definitions
- `steps/` - Individual step implementations
- `utils/` - Helper functions
- Clean separation of concerns

Start with the quick start example to see all features in action.