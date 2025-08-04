---
description: Get started with ZenML's prompt engineering features in 5 minutes - automatic versioning, GitHub-style diffs, and dashboard visualization.
---

# Quick Start

This guide walks you through ZenML's prompt engineering features with hands-on examples.

## Prerequisites

```bash
# Install ZenML with prompt engineering support
pip install zenml

# Initialize ZenML (if not already done)
zenml init
```

## 1. Basic Prompt Creation

```python
from zenml.prompts import Prompt, PromptType

# Create a simple prompt
prompt = Prompt(
    template="Answer this question: {question}",
    prompt_type=PromptType.USER,
    variables={"question": ""}
)

# Use the prompt
formatted = prompt.format(question="What is machine learning?")
print(formatted)
```

## 2. GitHub-Style Diff Comparison

```python
from zenml.prompts import Prompt, format_diff_for_console

# Create two different prompts
prompt_v1 = Prompt(
    template="Answer: {question}"
)

prompt_v2 = Prompt(
    template="Please provide a detailed answer to: {question}"
)

# Compare them with built-in diff functionality
diff_result = prompt_v1.diff(prompt_v2)

# View the comparison
print(f"Similarity: {diff_result['template_diff']['stats']['similarity_ratio']:.1%}")
print(f"Changes: {diff_result['template_diff']['stats']['total_changes']} lines")

# Pretty console output with colors
colored_diff = format_diff_for_console(diff_result['template_diff'])
print(colored_diff)
```

## 3. Compare LLM Outputs

```python
from zenml.prompts import compare_text_outputs

# Simulate different outputs from each prompt
v1_outputs = [
    "ML is a subset of AI.",
    "Neural networks mimic the brain."
]

v2_outputs = [
    "Machine learning is a subset of artificial intelligence that focuses on algorithms.",
    "Neural networks are computational models inspired by biological neural networks."
]

# Compare the outputs
comparison = compare_text_outputs(v1_outputs, v2_outputs)

print(f"Average similarity: {comparison['aggregate_stats']['average_similarity']:.1%}")
print(f"Changed outputs: {comparison['aggregate_stats']['changed_outputs']}")
print(f"Identical outputs: {comparison['aggregate_stats']['identical_outputs']}")
```

## 4. Use in ZenML Pipelines

```python
from zenml import step, pipeline
from zenml.prompts import Prompt

@step
def create_prompt() -> Prompt:
    """Create a prompt artifact (automatically versioned by ZenML)."""
    return Prompt(
        template="Summarize this article: {article}",
        variables={"article": ""}
    )

@step
def use_prompt(prompt: Prompt, articles: list) -> list:
    """Use the prompt with data."""
    return [prompt.format(article=article) for article in articles]

@pipeline
def prompt_pipeline():
    """Pipeline that creates and uses prompts."""
    prompt = create_prompt()
    articles = ["Sample article text..."]
    results = use_prompt(prompt, articles)
    return results

# Run the pipeline
pipeline_run = prompt_pipeline()
```

## 5. Dashboard Visualization

When you run pipelines with prompts:

1. **Navigate to your ZenML dashboard**
2. **View the pipeline run**
3. **Click on prompt artifacts** to see:
   - Syntax-highlighted templates
   - Variable tables and validation
   - HTML diff visualizations
   - Metadata and statistics

## 6. Advanced Comparison in Pipelines

```python
@step
def compare_prompt_versions(
    prompt1: Prompt, 
    prompt2: Prompt,
    test_data: list
) -> dict:
    """Compare two prompts using ZenML's core diff functionality."""
    
    # Use core diff functionality
    diff_result = prompt1.diff(prompt2, "Version 1", "Version 2")
    
    # Generate outputs for comparison
    outputs1 = [prompt1.format(question=q) for q in test_data]
    outputs2 = [prompt2.format(question=q) for q in test_data]
    
    # Compare outputs
    from zenml.prompts import compare_text_outputs
    output_comparison = compare_text_outputs(outputs1, outputs2)
    
    return {
        "prompt_diff": diff_result,
        "output_comparison": output_comparison,
        "recommendation": "Version 2" if output_comparison["aggregate_stats"]["average_similarity"] < 0.8 else "Similar"
    }
```

## Complete Example

Run the complete demo to see all features:

```bash
cd examples/prompt_engineering
python demo_diff.py
```

This demonstrates:
- ✅ Automatic prompt creation
- ✅ GitHub-style diff comparison with colors
- ✅ Output similarity analysis
- ✅ Core ZenML functions (no custom steps needed)

## Next Steps

- [Understanding Prompt Management](understanding-prompt-management.md) - Research and philosophy
- [Best Practices](best-practices.md) - Production guidance
- Explore `examples/prompt_engineering/` for more complex workflows

## Key Benefits

🎯 **Core ZenML functionality** - Available everywhere (pipelines, UI, notebooks, scripts)  
🔄 **Automatic versioning** - ZenML's artifact system handles versions  
📊 **GitHub-style diffs** - Built-in comparison with unified diffs, HTML, and statistics  
🎨 **Rich visualization** - Dashboard integration with syntax highlighting  
⚡ **Simple API** - `prompt1.diff(prompt2)` and `compare_text_outputs()`