---
description: Learn practical patterns for integrating prompts into your ZenML pipelines with versioning, templating, and variable management.
---

# Basic Prompt Workflows

This page covers the fundamental patterns for working with prompts in ZenML pipelines. You'll learn how to create, version, and use prompts in real workflows.

## Creating and Versioning Prompts

### Simple Prompt Creation

The most basic pattern is creating a versioned prompt:

```python
from zenml.prompts import Prompt

# Create a simple prompt
prompt = Prompt(
    template="Translate '{text}' from {source_language} to {target_language}",
    version="1.0",
    variables={"source_language": "English", "target_language": "Spanish"}
)

# Use the prompt
result = prompt.format(text="Hello world")
print(result)  # "Translate 'Hello world' from English to Spanish"
```

### Pipeline Integration

Prompts work seamlessly as ZenML artifacts in pipelines:

```python
from zenml import pipeline, step
from zenml.prompts import Prompt

@step
def create_translation_prompt(version: str = "1.0") -> Prompt:
    """Create a versioned translation prompt."""
    return Prompt(
        template="Translate '{text}' from {source_language} to {target_language}",
        version=version,
        variables={"source_language": "English", "target_language": "Spanish"}
    )

@step
def translate_text(prompt: Prompt, text: str) -> str:
    """Use the prompt to format translation request."""
    formatted_request = prompt.format(text=text)
    
    # In real usage, send to your LLM here
    # response = openai_client.chat.completions.create(...)
    
    return f"[LLM Response to: {formatted_request}]"

@pipeline
def translation_pipeline(text: str, prompt_version: str = "1.0"):
    """Pipeline that uses versioned prompts."""
    prompt = create_translation_prompt(version=prompt_version)
    result = translate_text(prompt=prompt, text=text)
    return result

# Run with different versions
result_v1 = translation_pipeline(text="Hello world", prompt_version="1.0")
result_v2 = translation_pipeline(text="Hello world", prompt_version="2.0")
```

## Variable Management Patterns

### Default Variables

Set common defaults to reduce repetition:

```python
# Prompt with sensible defaults
support_prompt = Prompt(
    template="""You are a {role} for {company}. 
    Customer question: {question}
    
    Please provide a {tone} response.""",
    version="1.0",
    variables={
        "role": "helpful customer support agent", 
        "company": "our company",
        "tone": "professional and friendly"
    }
)

# Override defaults as needed
formal_response = support_prompt.format(
    question="How do I cancel my subscription?",
    tone="formal and direct"
)
```

### Dynamic Variable Injection

Inject variables from pipeline context:

```python
@step
def create_context_aware_prompt(
    user_role: str, 
    company_name: str
) -> Prompt:
    """Create prompt with dynamic context."""
    return Prompt(
        template="You are assisting a {user_role} at {company_name}. Question: {question}",
        version="1.0",
        variables={
            "user_role": user_role,
            "company_name": company_name
        }
    )

@step
def get_user_context() -> tuple[str, str]:
    """Get user context from environment, database, etc."""
    return "software engineer", "TechCorp Inc"

@pipeline
def personalized_support_pipeline(question: str):
    """Pipeline with dynamic prompt context."""
    user_role, company = get_user_context()
    prompt = create_context_aware_prompt(user_role, company)
    
    # prompt now includes user-specific context
    formatted = prompt.format(question=question)
    return formatted
```

## Common Workflow Patterns

### Pattern 1: Simple Question-Answering

```python
@step
def create_qa_prompt() -> Prompt:
    return Prompt(
        template="""Context: {context}
        
        Question: {question}
        
        Please provide a clear, accurate answer based on the context provided.""",
        version="1.0"
    )

@step
def answer_question(prompt: Prompt, context: str, question: str) -> str:
    formatted_prompt = prompt.format(context=context, question=question)
    # Send to LLM and return response
    return formatted_prompt  # Placeholder

@pipeline
def qa_pipeline(context: str, question: str):
    prompt = create_qa_prompt()
    answer = answer_question(prompt, context, question)
    return answer
```

### Pattern 2: Multi-Step Reasoning

```python
@step
def create_reasoning_prompts() -> tuple[Prompt, Prompt, Prompt]:
    """Create prompts for multi-step reasoning."""
    
    analysis_prompt = Prompt(
        template="Analyze this problem: {problem}\n\nBreak it down into key components:",
        version="1.0"
    )
    
    solution_prompt = Prompt(
        template="Based on this analysis: {analysis}\n\nPropose a solution:",
        version="1.0"
    )
    
    validation_prompt = Prompt(
        template="Evaluate this solution: {solution}\n\nIs it correct? Explain:",
        version="1.0"
    )
    
    return analysis_prompt, solution_prompt, validation_prompt

@pipeline
def reasoning_pipeline(problem: str):
    """Multi-step reasoning with different prompts."""
    analysis_prompt, solution_prompt, validation_prompt = create_reasoning_prompts()
    
    # Step 1: Analyze
    analysis = llm_step(analysis_prompt, problem=problem)
    
    # Step 2: Solve
    solution = llm_step(solution_prompt, analysis=analysis)
    
    # Step 3: Validate
    validation = llm_step(validation_prompt, solution=solution)
    
    return {"analysis": analysis, "solution": solution, "validation": validation}
```

### Pattern 3: Few-Shot Learning

```python
@step
def create_few_shot_prompt() -> Prompt:
    """Create prompt with few-shot examples."""
    template = """Here are some examples of good customer responses:

Example 1:
Customer: "I'm having trouble logging in"
Response: "I'd be happy to help you with login issues. Let me guide you through some troubleshooting steps..."

Example 2:  
Customer: "When will my order arrive?"
Response: "I can help you track your order. Let me look up the shipping details for you..."

Now respond to this customer:
Customer: "{customer_message}"
Response:"""

    return Prompt(template=template, version="1.0")

@pipeline
def few_shot_support_pipeline(customer_message: str):
    prompt = create_few_shot_prompt()
    response = llm_step(prompt, customer_message=customer_message)
    return response
```

## Version Evolution Patterns

### Iterative Improvement

```python
# Version 1.0 - Basic
prompt_v1 = Prompt(
    template="Summarize: {text}",
    version="1.0"
)

# Version 2.0 - More specific
prompt_v2 = Prompt(
    template="Write a concise summary of the following text in {max_sentences} sentences: {text}",
    version="2.0",
    variables={"max_sentences": "3"}
)

# Version 3.0 - Domain-specific
prompt_v3 = Prompt(
    template="""Summarize this {document_type} for a {audience} audience.

Text: {text}

Summary (max {max_sentences} sentences):""",
    version="3.0",
    variables={
        "document_type": "document",
        "audience": "general", 
        "max_sentences": "3"
    }
)
```

### A/B Testing Evolution

```python
@step
def create_prompt_variants() -> tuple[Prompt, Prompt]:
    """Create two prompt variants for testing."""
    
    # Current production version
    current = Prompt(
        template="Answer this question: {question}",
        version="1.0"
    )
    
    # New candidate version
    candidate = Prompt(
        template="Please provide a helpful answer to this question: {question}",
        version="1.1"
    )
    
    return current, candidate

@pipeline
def ab_test_pipeline(question: str):
    """Test both prompts and compare results."""
    current, candidate = create_prompt_variants()
    
    result_current = llm_step(current, question=question)
    result_candidate = llm_step(candidate, question=question)
    
    # Compare results (implement your evaluation logic)
    comparison = compare_responses(result_current, result_candidate)
    
    return {
        "current": result_current,
        "candidate": result_candidate,
        "comparison": comparison
    }
```

## Error Handling and Validation

### Variable Validation

```python
@step
def create_validated_prompt(template: str, required_vars: list[str]) -> Prompt:
    """Create prompt with variable validation."""
    prompt = Prompt(template=template, version="1.0")
    
    # Check for required variables
    template_vars = prompt.get_variable_names()
    missing_vars = [var for var in required_vars if var not in template_vars]
    
    if missing_vars:
        raise ValueError(f"Template missing required variables: {missing_vars}")
    
    return prompt

@step  
def safe_format_prompt(prompt: Prompt, **kwargs) -> str:
    """Safely format prompt with error handling."""
    try:
        return prompt.format(**kwargs)
    except ValueError as e:
        # Log error and return safe default
        print(f"Prompt formatting error: {e}")
        return f"Error formatting prompt with variables: {list(kwargs.keys())}"
```

## Best Practices for Workflow Design

### ✅ Do's

- **Keep prompts focused**: One clear purpose per prompt
- **Use meaningful versions**: `v1.0`, `v2.0`, not random strings  
- **Set sensible defaults**: Reduce repetition with good default variables
- **Test incrementally**: Small changes between versions
- **Document changes**: Clear commit messages for prompt updates

### ❌ Don'ts  

- **Avoid complex templating**: Keep templates readable
- **Don't mix concerns**: Separate prompts for different tasks
- **Don't skip validation**: Check required variables exist
- **Avoid magic values**: Make important values into variables
- **Don't ignore errors**: Handle formatting failures gracefully

## Next Steps

Now that you understand basic workflows, explore advanced topics:

- [Version control and A/B testing](version-control-and-testing.md) - Systematic comparison strategies
- [Dashboard integration](dashboard-integration.md) - Visualizing prompts and results
- [Best practices](best-practices.md) - Production-ready patterns

These workflow patterns provide the foundation for scalable prompt engineering in ZenML. Start with simple patterns and evolve them as your needs grow.