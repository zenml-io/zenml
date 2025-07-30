---
description: Master A/B testing strategies for prompts with ZenML's built-in comparison utilities and systematic evaluation approaches.
---

# Version Control and A/B Testing

This page covers systematic approaches to prompt testing and version control. You'll learn how to compare prompt versions, track performance over time, and make data-driven decisions about prompt improvements.

## A/B Testing Fundamentals

### Simple A/B Comparison

The most basic A/B test compares two prompt versions on the same test cases:

```python
from zenml import pipeline, step
from zenml.prompts import Prompt

@step
def create_test_prompts() -> tuple[Prompt, Prompt]:
    """Create two prompts for A/B testing."""
    prompt_a = Prompt(
        template="Answer briefly: {question}",
        version="1.0"
    )
    
    prompt_b = Prompt(
        template="Provide a detailed answer: {question}", 
        version="2.0"
    )
    
    return prompt_a, prompt_b

@step
def run_ab_test(
    prompt_a: Prompt, 
    prompt_b: Prompt,
    test_questions: list[str]
) -> dict:
    """Compare two prompts on test questions."""
    results = {
        "prompt_a_version": prompt_a.version,
        "prompt_b_version": prompt_b.version,
        "test_results": []
    }
    
    for question in test_questions:
        # Format both prompts
        formatted_a = prompt_a.format(question=question)
        formatted_b = prompt_b.format(question=question)
        
        # Get responses (replace with actual LLM calls)
        response_a = llm_call(formatted_a)
        response_b = llm_call(formatted_b)
        
        # Evaluate responses
        score_a = evaluate_response(response_a, question)
        score_b = evaluate_response(response_b, question)
        
        results["test_results"].append({
            "question": question,
            "prompt_a_score": score_a,
            "prompt_b_score": score_b,
            "winner": "A" if score_a > score_b else "B"
        })
    
    # Calculate overall winner
    wins_a = sum(1 for r in results["test_results"] if r["winner"] == "A")
    wins_b = len(results["test_results"]) - wins_a
    results["overall_winner"] = "A" if wins_a > wins_b else "B"
    
    return results

@pipeline
def ab_test_pipeline(test_questions: list[str]):
    """Run A/B test comparing two prompt versions."""
    prompt_a, prompt_b = create_test_prompts()
    results = run_ab_test(prompt_a, prompt_b, test_questions)
    return results
```

### Multi-Metric Evaluation

For more sophisticated testing, evaluate prompts on multiple metrics:

```python
@step
def evaluate_prompt_comprehensively(
    prompt: Prompt,
    test_cases: list[dict],
    metrics: dict
) -> dict:
    """Evaluate prompt on multiple metrics."""
    results = {
        "prompt_version": prompt.version,
        "metrics": {},
        "individual_results": []
    }
    
    all_scores = {metric: [] for metric in metrics.keys()}
    
    for test_case in test_cases:
        # Format and get response
        formatted_prompt = prompt.format(**test_case["inputs"])
        response = llm_call(formatted_prompt)
        
        # Evaluate on each metric
        case_scores = {}
        for metric_name, metric_func in metrics.items():
            score = metric_func(response, test_case.get("expected"))
            case_scores[metric_name] = score
            all_scores[metric_name].append(score)
        
        results["individual_results"].append({
            "test_case": test_case,
            "response": response,
            "scores": case_scores
        })
    
    # Calculate aggregate metrics
    for metric_name, scores in all_scores.items():
        results["metrics"][metric_name] = {
            "average": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "std": calculate_std(scores)
        }
    
    return results

# Define your evaluation metrics
evaluation_metrics = {
    "accuracy": lambda response, expected: calculate_accuracy(response, expected),
    "relevance": lambda response, expected: calculate_relevance(response, expected),
    "clarity": lambda response, expected: calculate_clarity(response),
    "length": lambda response, expected: len(response.split())
}

@pipeline  
def comprehensive_evaluation_pipeline(test_cases: list[dict]):
    """Evaluate prompts on multiple metrics."""
    prompt_a, prompt_b = create_test_prompts()
    
    results_a = evaluate_prompt_comprehensively(prompt_a, test_cases, evaluation_metrics)
    results_b = evaluate_prompt_comprehensively(prompt_b, test_cases, evaluation_metrics)
    
    # Compare results
    comparison = compare_comprehensive_results(results_a, results_b)
    
    return {
        "prompt_a_results": results_a,
        "prompt_b_results": results_b, 
        "comparison": comparison
    }
```

## Statistical Significance Testing

### Sample Size and Confidence

For production decisions, ensure statistical significance:

```python
import scipy.stats as stats

@step
def statistical_ab_test(
    prompt_a: Prompt,
    prompt_b: Prompt, 
    test_cases: list[dict],
    confidence_level: float = 0.95
) -> dict:
    """Run statistically rigorous A/B test."""
    
    scores_a = []
    scores_b = []
    
    for test_case in test_cases:
        # Get responses for both prompts
        response_a = llm_call(prompt_a.format(**test_case["inputs"]))
        response_b = llm_call(prompt_b.format(**test_case["inputs"]))
        
        # Score responses (0-1 scale)
        score_a = evaluate_response_quality(response_a, test_case)
        score_b = evaluate_response_quality(response_b, test_case)
        
        scores_a.append(score_a)
        scores_b.append(score_b)
    
    # Statistical analysis
    mean_a, mean_b = sum(scores_a) / len(scores_a), sum(scores_b) / len(scores_b)
    
    # T-test for significance
    t_stat, p_value = stats.ttest_ind(scores_a, scores_b)
    
    # Effect size (Cohen's d)
    pooled_std = ((len(scores_a) - 1) * stats.stdev(scores_a)**2 + 
                  (len(scores_b) - 1) * stats.stdev(scores_b)**2) / (len(scores_a) + len(scores_b) - 2)
    cohens_d = (mean_a - mean_b) / (pooled_std ** 0.5)
    
    # Confidence interval
    alpha = 1 - confidence_level
    critical_value = stats.t.ppf(1 - alpha/2, len(scores_a) + len(scores_b) - 2)
    margin_of_error = critical_value * (pooled_std * (1/len(scores_a) + 1/len(scores_b))) ** 0.5
    
    return {
        "prompt_a_version": prompt_a.version,
        "prompt_b_version": prompt_b.version,
        "mean_score_a": mean_a,
        "mean_score_b": mean_b,
        "difference": mean_b - mean_a,
        "p_value": p_value,
        "is_significant": p_value < alpha,
        "effect_size": cohens_d,
        "confidence_interval": (mean_b - mean_a - margin_of_error, mean_b - mean_a + margin_of_error),
        "sample_size": len(test_cases),
        "recommendation": "Use B" if (p_value < alpha and mean_b > mean_a) else 
                         "Use A" if (p_value < alpha and mean_a > mean_b) else 
                         "No significant difference"
    }
```

## Version Control Strategies

### Semantic Versioning for Prompts

Use meaningful version numbers that indicate the type of change:

```python
# Major version: Fundamental prompt structure change
prompt_v1 = Prompt(
    template="Answer: {question}",
    version="1.0.0"
)

prompt_v2 = Prompt(
    template="You are a helpful assistant. Question: {question}\nAnswer:",
    version="2.0.0"  # Major change: different structure
)

# Minor version: Enhanced functionality  
prompt_v2_1 = Prompt(
    template="You are a helpful assistant specializing in {domain}. Question: {question}\nAnswer:",
    version="2.1.0",  # Minor change: added domain variable
    variables={"domain": "general topics"}
)

# Patch version: Small improvements
prompt_v2_1_1 = Prompt(
    template="You are a helpful assistant specializing in {domain}. Question: {question}\n\nProvide a clear, accurate answer:",
    version="2.1.1"  # Patch: clarified instructions
)
```

### Git Integration Patterns

Store prompts in version control alongside your code:

```python
# prompts/customer_support.py
class CustomerSupportPrompts:
    """Version-controlled customer support prompts."""
    
    @staticmethod
    def basic_response_v1() -> Prompt:
        return Prompt(
            template="""You are a customer support agent for {company_name}.
            
Customer question: {question}

Provide a helpful, professional response.""",
            version="1.0.0",
            variables={"company_name": "our company"}
        )
    
    @staticmethod 
    def basic_response_v2() -> Prompt:
        return Prompt(
            template="""You are a friendly customer support agent for {company_name}.

Customer: {question}

Please provide a helpful response that:
- Addresses their specific concern
- Offers next steps if applicable  
- Maintains a {tone} tone""",
            version="2.0.0",
            variables={
                "company_name": "our company",
                "tone": "professional yet warm"
            }
        )

# In your pipeline
@step
def get_current_support_prompt() -> Prompt:
    """Get the current production support prompt."""
    return CustomerSupportPrompts.basic_response_v2()
```

### Environment-Based Versioning

Use different prompt versions for different environments:

```python
import os

@step
def get_environment_prompt() -> Prompt:
    """Get prompt based on deployment environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        # Stable, well-tested prompt
        return Prompt(
            template="Answer concisely: {question}",
            version="1.2.0"
        )
    elif env == "staging":
        # Latest candidate for production
        return Prompt(
            template="Provide a brief, accurate answer: {question}",
            version="1.3.0-rc1"
        )
    else:
        # Development version with extra debugging
        return Prompt(
            template="[DEBUG MODE] Answer: {question}",
            version="1.3.0-dev"
        )
```

## Advanced Testing Patterns

### Gradual Rollout Testing

Test new prompts with a small percentage of traffic:

```python
import random

@step
def gradual_rollout_test(
    current_prompt: Prompt,
    candidate_prompt: Prompt,
    rollout_percentage: float = 0.1
) -> Prompt:
    """Gradually roll out new prompt to small percentage of traffic."""
    
    if random.random() < rollout_percentage:
        print(f"Using candidate prompt v{candidate_prompt.version}")
        return candidate_prompt
    else:
        print(f"Using current prompt v{current_prompt.version}")
        return current_prompt

@pipeline
def gradual_rollout_pipeline(question: str):
    """Pipeline with gradual rollout testing."""
    current = Prompt(template="Answer: {question}", version="1.0")
    candidate = Prompt(template="Provide answer: {question}", version="1.1")
    
    # 10% of traffic gets new prompt
    selected_prompt = gradual_rollout_test(current, candidate, rollout_percentage=0.1)
    
    response = llm_step(selected_prompt, question=question)
    
    # Log which version was used for analysis
    return {
        "response": response,
        "prompt_version": selected_prompt.version,
        "question": question
    }
```

### Multi-Armed Bandit Testing

Dynamically adjust traffic based on performance:

```python
@step
def bandit_prompt_selection(
    prompts: list[Prompt],
    performance_history: dict
) -> Prompt:
    """Select prompt using epsilon-greedy bandit algorithm."""
    epsilon = 0.1  # Exploration rate
    
    if random.random() < epsilon:
        # Explore: random selection
        selected = random.choice(prompts)
        print(f"Exploring with prompt v{selected.version}")
    else:
        # Exploit: select best performing
        best_version = max(performance_history.keys(), 
                          key=lambda v: performance_history[v]["avg_score"])
        selected = next(p for p in prompts if p.version == best_version)
        print(f"Exploiting with best prompt v{selected.version}")
    
    return selected
```

## Testing Best Practices

### ✅ Do's

- **Use representative test cases**: Test with real user scenarios
- **Measure what matters**: Focus on business-relevant metrics  
- **Ensure statistical significance**: Don't make decisions on small samples
- **Document test methodology**: Make results reproducible
- **Test incrementally**: Small changes are easier to understand

### ❌ Don'ts

- **Don't test in isolation**: Consider context and user experience
- **Don't ignore edge cases**: Test with unusual or challenging inputs
- **Don't rush decisions**: Allow sufficient data collection time
- **Don't forget baselines**: Always compare against current performance
- **Don't skip validation**: Verify results make intuitive sense

## Integration with ZenML Dashboard

All testing results automatically appear in your ZenML dashboard:

- **Prompt versions** shown as artifacts with full visualization
- **A/B test results** tracked across pipeline runs
- **Performance metrics** graphed over time
- **Statistical significance** indicated in comparison views

## Next Steps

Now that you understand version control and testing strategies:

- [Dashboard integration](dashboard-integration.md) - Visualize your testing results
- [Best practices](best-practices.md) - Production patterns from experienced teams

The key to successful prompt engineering is systematic testing and data-driven decision making. Use these patterns to confidently improve your prompts over time.