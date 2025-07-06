# ZenML Prompt Engineering Example

This example demonstrates how to use ZenML's prompt abstraction for LLMOps workflows. It shows best practices for creating, managing, and experimenting with prompts using ZenML pipelines.

## Overview

ZenML treats prompts as first-class artifacts that can be versioned, tracked, and experimented with through pipelines. This example showcases:

- Creating and managing prompts as ZenML artifacts
- Building pipelines for prompt evaluation and comparison
- Integrating with LLM providers (OpenAI, Anthropic)
- Using ZenML's experiment tracking for prompt optimization
- Template runs for systematic prompt experimentation

## Prerequisites

- ZenML installed: `pip install zenml`
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- Optional: Anthropic API key for Claude models (`ANTHROPIC_API_KEY`)

## Structure

```
prompt_engineering/
├── README.md                    # This file
├── pipelines.py                # Pipeline definitions
├── steps.py                    # Step implementations
├── prompts/                    # Example prompt templates
│   ├── qa_prompts.json        # Question-answering prompts
│   └── summarization_prompts.json  # Summarization prompts
└── run.py                      # Script to run the examples
```

## Quick Start

1. **Set up environment:**
```bash
export OPENAI_API_KEY="your-api-key"
# Optional for Claude:
export ANTHROPIC_API_KEY="your-anthropic-key"
```

2. **Run the basic example:**
```bash
python run.py --pipeline basic
```

3. **Run prompt comparison:**
```bash
python run.py --pipeline comparison
```

## Example 1: Basic Prompt Pipeline

This pipeline demonstrates the fundamental workflow of creating, formatting, and using prompts with an LLM.

```python
@pipeline
def prompt_development_pipeline():
    """Basic pipeline for prompt development and testing."""
    # Create a prompt artifact
    prompt = create_prompt_step(
        template="You are a helpful assistant. Answer this question: {question}",
        prompt_type="user",
        task="question_answering"
    )
    
    # Format and test the prompt
    test_results = test_prompt_with_llm_step(
        prompt=prompt,
        test_cases=[
            {"question": "What is machine learning?"},
            {"question": "How does ZenML work?"}
        ],
        model="gpt-3.5-turbo"
    )
    
    # Evaluate results
    evaluation = evaluate_prompt_step(prompt, test_results)
    
    return prompt, evaluation
```

### Key Concepts:

- **Prompt as Artifact**: The prompt is created as a ZenML artifact that can be tracked and versioned
- **Separation of Concerns**: Prompt creation, testing, and evaluation are separate steps
- **LLM Integration**: Direct integration with OpenAI/Anthropic SDKs within steps

## Example 2: Prompt Comparison Pipeline

This pipeline shows how to compare multiple prompt variants and select the best one.

```python
@pipeline
def prompt_comparison_pipeline():
    """Pipeline for comparing multiple prompt variants."""
    # Create base prompt
    base_prompt = create_prompt_step(
        template="Answer the question: {question}",
        prompt_type="user"
    )
    
    # Create variants
    variant_1 = create_variant_step(
        base_prompt,
        template="You are an expert. Answer: {question}",
        variant_name="expert_variant"
    )
    
    variant_2 = create_variant_step(
        base_prompt,
        template="Think step by step and answer: {question}",
        variant_name="cot_variant"
    )
    
    # Test all variants
    test_dataset = load_test_dataset_step()
    
    base_results = test_prompt_with_llm_step(base_prompt, test_dataset)
    v1_results = test_prompt_with_llm_step(variant_1, test_dataset)
    v2_results = test_prompt_with_llm_step(variant_2, test_dataset)
    
    # Compare and select best
    comparison = compare_prompts_step(
        prompts=[base_prompt, variant_1, variant_2],
        results=[base_results, v1_results, v2_results]
    )
    
    best_prompt = select_best_prompt_step(comparison)
    
    return best_prompt, comparison
```

### Using Template Runs

To run multiple experiments with different configurations:

```bash
# Run with different models
python run.py --pipeline comparison --model gpt-4
python run.py --pipeline comparison --model claude-3

# Run with different test datasets
python run.py --pipeline comparison --dataset qa_hard
python run.py --pipeline comparison --dataset qa_easy
```

## Working with Prompts

### Creating Prompts

```python
from zenml.prompts import Prompt

# Simple prompt
prompt = Prompt(
    template="Translate this to {language}: {text}",
    variables={"language": "French"}  # Default values
)

# Advanced prompt with examples
prompt = Prompt(
    template="Answer the question based on the context.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:",
    prompt_type="user",
    task="question_answering",
    examples=[
        {
            "context": "The sky is blue.",
            "question": "What color is the sky?",
            "answer": "Blue"
        }
    ],
    instructions="Be concise and accurate. Only use information from the context."
)
```

### Using Prompts in Steps

```python
@step
def use_prompt_step(prompt: Prompt) -> str:
    """Example of using a prompt in a step."""
    import openai
    
    # Format the prompt with specific values
    formatted = prompt.format(
        question="What is ZenML?",
        context="ZenML is an MLOps framework..."
    )
    
    # Use with OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": formatted}]
    )
    
    return response.choices[0].message.content
```

## Best Practices

1. **Version Control**: Use ZenML's artifact versioning to track prompt iterations
2. **Systematic Testing**: Always test prompts with diverse test cases
3. **Metrics Tracking**: Use ZenML's experiment tracking to monitor performance
4. **Template Variables**: Use meaningful variable names in templates
5. **Modular Steps**: Keep prompt operations in separate, reusable steps

## Advanced Usage

### Custom Evaluation Metrics

```python
@step
def custom_evaluation_step(
    prompt: Prompt,
    results: List[Dict[str, str]]
) -> Dict[str, float]:
    """Custom evaluation logic for prompts."""
    # Implement domain-specific evaluation
    metrics = {
        "accuracy": calculate_accuracy(results),
        "relevance": calculate_relevance(results),
        "coherence": calculate_coherence(results)
    }
    
    return metrics
```

### Integration with ZenML Experiment Tracking

```python
from zenml.client import Client

# After running pipelines, compare experiments
client = Client()
runs = client.list_pipeline_runs(
    pipeline_name="prompt_comparison_pipeline"
)

# Analyze results across runs
for run in runs:
    artifacts = run.artifacts
    # Access prompt artifacts and metrics
```

## Troubleshooting

- **API Keys**: Ensure your LLM API keys are set as environment variables
- **Dependencies**: Install required packages: `pip install openai anthropic`
- **Rate Limits**: Add retry logic for API rate limits in production

## Next Steps

- Explore prompt versioning with ZenML's Model Registry
- Build more complex evaluation pipelines
- Integrate with your existing ML workflows
- Create custom materializers for specialized prompt types

For more information, see the [ZenML documentation](https://docs.zenml.io).