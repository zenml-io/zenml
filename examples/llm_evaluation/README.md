# LLM-as-Judge Prompt Evaluation with ZenML

This example demonstrates how to use ZenML's LLM-as-Judge evaluation framework to systematically assess and compare prompt quality using automated evaluation criteria.

## Overview

The LLM-as-Judge methodology uses a large language model to evaluate the quality of AI-generated responses based on specific criteria such as relevance, accuracy, clarity, and safety. This approach provides consistent, scalable evaluation for prompt engineering and optimization.

## Features

- **Automated Quality Assessment**: Evaluate prompts using multiple criteria
- **Version Comparison**: Compare different prompt versions to identify improvements
- **Comprehensive Reports**: Get detailed evaluation results with recommendations
- **ZenML Integration**: Leverage ZenML's pipeline orchestration for scalable evaluation
- **Configurable Criteria**: Define custom evaluation criteria for your use case

## Quick Start

### 1. Install Dependencies

```bash
pip install zenml[server] openai  # or your preferred LLM provider
```

### 2. Set Up Your Environment

```bash
# Start ZenML server
zenml up

# Set up your LLM API credentials (example for OpenAI)
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Create Prompt Artifacts

First, create some prompt artifacts in ZenML that you want to evaluate:

```python
from zenml import step, pipeline
from zenml.client import Client

@step
def create_prompt_artifact(template: str, metadata: dict) -> str:
    """Create a prompt artifact in ZenML."""
    from zenml.artifacts.utils import save_artifact
    
    artifact = save_artifact(
        data=template,
        name="my_prompt_template",
        artifact_type="prompt",
        metadata=metadata
    )
    return artifact.id

@pipeline
def create_prompts_pipeline():
    """Pipeline to create example prompt artifacts."""
    
    # Create a customer service prompt
    prompt1 = create_prompt_artifact(
        template="""You are a helpful customer service assistant.

Customer Question: {question}
Customer Context: {context}

Please provide a helpful and professional response.""",
        metadata={
            "task": "customer_service",
            "domain": "support",
            "template_length": 150,
            "variable_count": 2
        }
    )
    
    # Create an improved version
    prompt2 = create_prompt_artifact(
        template="""You are a professional customer service representative committed to providing excellent support.

Customer Information:
- Question: {question}
- Context: {context}
- Previous Interactions: {history}

Instructions:
1. Address the customer's question directly
2. Use a warm, professional tone
3. Provide actionable solutions when possible
4. Offer additional assistance if appropriate

Response:""",
        metadata={
            "task": "customer_service",
            "domain": "support", 
            "template_length": 380,
            "variable_count": 3,
            "version": "improved"
        }
    )

if __name__ == "__main__":
    create_prompts_pipeline()
```

### 4. Run Evaluation Pipeline

```python
from evaluate_prompts_pipeline import prompt_evaluation_pipeline

# Get your prompt artifact IDs
client = Client()
prompts = client.list_artifacts(artifact_type="prompt")
prompt_ids = [p.id for p in prompts.items[:2]]

# Run evaluation
evaluation_report = prompt_evaluation_pipeline(
    prompt_ids=prompt_ids,
    comparison_pairs=[(prompt_ids[0], prompt_ids[1])] if len(prompt_ids) >= 2 else None
)

print("Evaluation completed!")
print(f"Average score: {evaluation_report['evaluation_summary']['average_overall_score']:.2f}")
```

## Configuration

### Evaluation Criteria

The framework supports various evaluation criteria:

- **Relevance**: How relevant is the response to the input
- **Accuracy**: Technical accuracy of the information  
- **Clarity**: How clear and understandable the response is
- **Completeness**: Whether the response fully addresses the question
- **Helpfulness**: How helpful the response is to the user
- **Safety**: Whether the response is safe and appropriate

You can customize criteria when calling the evaluation steps:

```python
custom_criteria = ["relevance", "clarity", "brand_alignment", "actionability"]

evaluation = llm_judge_evaluate_prompt(
    prompt_artifact_id="your-prompt-id",
    test_cases=test_cases,
    evaluation_criteria=custom_criteria,
    judge_model="gpt-4",
    temperature=0.1
)
```

### Test Cases

Define test cases that represent realistic usage scenarios:

```python
test_cases = [
    {
        "variables": {
            "question": "How do I return a damaged product?",
            "context": "Customer received broken item 2 days ago",
            "history": "First time customer, no previous returns"
        },
        "expected_output": "Clear return process with empathy and urgency"
    },
    {
        "variables": {
            "question": "What is your refund policy?", 
            "context": "Customer bought item 45 days ago",
            "history": "Regular customer, 3 previous purchases"
        },
        "expected_output": "Policy explanation with consideration for customer loyalty"
    }
]
```

### Judge Models

Supported judge models:
- `gpt-4`: Most accurate, higher cost
- `gpt-3.5-turbo`: Good balance of accuracy and cost
- `claude-3-sonnet`: Alternative to OpenAI models

## Integration with ZenML Cloud UI

The evaluation framework integrates with ZenML Cloud UI, providing:

1. **Evaluation Dialog**: Configure and launch evaluations from the UI
2. **Results Dashboard**: View detailed evaluation results and comparisons
3. **Analytics Integration**: Track prompt performance over time
4. **Quality Metrics**: Monitor prompt quality trends

Access the evaluation features in the ZenML Cloud UI under:
- **Prompts → Analytics Tab**: Run evaluations and view results
- **Individual Prompt Pages**: Evaluate specific prompt artifacts

## Advanced Usage

### Custom Evaluation Pipeline

Create custom evaluation pipelines for specific use cases:

```python
@pipeline
def custom_evaluation_pipeline(
    prompt_ids: List[str],
    domain_specific_criteria: List[str]
):
    \"\"\"Custom evaluation pipeline with domain-specific criteria.\"\"\"
    
    # Load domain-specific test cases
    test_cases = load_domain_test_cases()
    
    # Run evaluations with custom criteria
    results = []
    for prompt_id in prompt_ids:
        evaluation = llm_judge_evaluate_prompt(
            prompt_artifact_id=prompt_id,
            test_cases=test_cases,
            evaluation_criteria=domain_specific_criteria,
            judge_model="gpt-4"
        )
        results.append(evaluation)
    
    # Generate domain-specific report
    report = generate_domain_report(results)
    return report
```

### Continuous Evaluation

Set up continuous evaluation for prompt optimization:

```python
@step 
def monitor_prompt_quality(prompt_id: str) -> bool:
    \"\"\"Monitor prompt quality and trigger alerts if quality drops.\"\"\"
    
    evaluation = llm_judge_evaluate_prompt(
        prompt_artifact_id=prompt_id,
        test_cases=get_monitoring_test_cases(),
        evaluation_criteria=["relevance", "accuracy", "safety"]
    )
    
    # Check if quality meets threshold
    quality_threshold = 0.8
    if evaluation["overall_score"] < quality_threshold:
        send_quality_alert(prompt_id, evaluation)
        return False
    
    return True

@pipeline(schedule="@daily")
def daily_prompt_monitoring():
    \"\"\"Daily monitoring of production prompts.\"\"\"
    
    # Get production prompt artifacts
    production_prompts = get_production_prompts()
    
    for prompt_id in production_prompts:
        monitor_prompt_quality(prompt_id)
```

## Best Practices

### 1. Test Case Design
- Include diverse, realistic scenarios
- Cover edge cases and potential failure modes
- Use consistent evaluation criteria across test cases
- Update test cases based on real user interactions

### 2. Evaluation Criteria
- Choose criteria relevant to your specific use case
- Balance comprehensiveness with evaluation cost
- Consider both technical and subjective quality measures
- Document criteria definitions for consistency

### 3. Judge Model Selection
- Use more powerful models (GPT-4) for critical evaluations
- Consider cost vs. accuracy trade-offs
- Validate judge model reliability with human evaluation
- Use consistent models for comparison studies

### 4. Results Interpretation
- Consider confidence intervals and statistical significance
- Validate automated results with human evaluation
- Track evaluation trends over time
- Use results to inform prompt engineering decisions

## Troubleshooting

### Common Issues

1. **LLM API Errors**: Ensure API keys are set and you have sufficient credits
2. **Inconsistent Evaluations**: Lower temperature values for more consistent results
3. **High Evaluation Costs**: Use smaller test case sets or less expensive judge models
4. **Poor Judge Performance**: Validate judge model with known good/bad examples

### Performance Optimization

- Cache evaluation results to avoid re-running identical evaluations
- Use parallel execution for multiple prompt evaluations
- Batch API calls when possible to reduce latency
- Monitor and optimize evaluation costs

## Contributing

To contribute to the LLM evaluation framework:

1. Fork the ZenML repository
2. Create a feature branch for your changes
3. Add tests for new functionality
4. Submit a pull request with detailed description

## Support

For questions and support:
- [ZenML Documentation](https://docs.zenml.io)
- [ZenML Discord Community](https://zenml.io/slack)
- [GitHub Issues](https://github.com/zenml-io/zenml/issues)

## License

This example is part of ZenML and is licensed under the Apache 2.0 License.