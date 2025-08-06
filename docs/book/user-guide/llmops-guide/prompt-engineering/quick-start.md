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

When you run pipelines with prompts and responses:

1. **Navigate to your ZenML dashboard**
2. **View the pipeline run**
3. **Click on Prompt artifacts** to see:
   - Syntax-highlighted templates
   - Variable tables and validation
   - **JSON schema visualization** with properties and types
   - **Few-shot examples** with input/output pairs
   - HTML diff visualizations
   - Metadata and statistics
4. **Click on PromptResponse artifacts** to see:
   - **Response content** with syntax highlighting
   - **Cost breakdown** (tokens, pricing, efficiency)
   - **Quality metrics** and validation results
   - **Performance data** (response time, token usage)
   - **Provenance links** back to source prompts

## 6. Enhanced Prompts with Schemas and Examples

```python
from zenml.prompts import Prompt
from pydantic import BaseModel

# Define output schema
class InvoiceData(BaseModel):
    invoice_number: str
    amount: float
    vendor: str

# Create enhanced prompt with schema and examples
enhanced_prompt = Prompt(
    template="Extract invoice data from: {document_text}",
    output_schema=InvoiceData.model_json_schema(),
    examples=[
        {
            "input": {"document_text": "Invoice #INV-001 from ACME Corp for $500"},
            "output": {
                "invoice_number": "INV-001", 
                "amount": 500.0,
                "vendor": "ACME Corp"
            }
        }
    ],
    variables={"document_text": ""}
)

# Use with format_with_examples to include examples in prompt
formatted_with_examples = enhanced_prompt.format_with_examples(
    document_text="Invoice #INV-123 from XYZ Inc for $250"
)
```

## 7. Response Tracking

```python
from zenml.prompts import PromptResponse
from datetime import datetime

# Create comprehensive response artifact
response = PromptResponse(
    content='{"invoice_number": "INV-123", "amount": 250.0, "vendor": "XYZ Inc"}',
    parsed_output={"invoice_number": "INV-123", "amount": 250.0, "vendor": "XYZ Inc"},
    model_name="gpt-4",
    prompt_tokens=150,
    completion_tokens=45,
    total_cost=0.003,
    quality_score=0.95,
    validation_passed=True,
    created_at=datetime.now()
)

# Check response validity
print(f"Valid response: {response.is_valid_response()}")
print(f"Token efficiency: {response.get_token_efficiency():.1%}")
print(f"Cost per token: ${response.get_cost_per_token():.6f}")
```

## 8. Advanced Comparison in Pipelines

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