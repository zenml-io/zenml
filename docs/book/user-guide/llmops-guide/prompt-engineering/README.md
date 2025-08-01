---
description: Streamline your prompt development workflow with simple versioning, A/B testing, and dashboard integration in ZenML.
icon: edit
---

# Prompt Engineering

Welcome to ZenML's Prompt Engineering guide, where we explore a streamlined approach to managing prompts in your LLM workflows. Based on extensive user research, this guide focuses on the three core features teams actually need: **simple versioning**, **dashboard visualization**, and **A/B comparison**.

<figure><img src="../../.gitbook/assets/prompt-engineering-overview.png" alt=""><figcaption><p>ZenML provides Git-like prompt versioning with built-in A/B testing and dashboard visualization.</p></figcaption></figure>

## What You'll Learn

Unlike complex prompt management systems, ZenML's approach focuses on simplicity and practicality:

* [Prompt Engineering in 20 lines](prompt-engineering-30-loc.md) - Get started immediately with a working example
* [Understanding Prompt Management](understanding-prompt-management.md) - Learn why simple versioning beats complex systems
* [Basic Prompt Workflows](basic-prompt-workflows.md) - Create, version, and format prompts in ZenML pipelines
* [Version Control and A/B Testing](version-control-and-testing.md) - Compare prompt versions with built-in utilities
* [Dashboard Integration](dashboard-integration.md) - Visualize prompts and track performance across runs
* [Best Practices](best-practices.md) - Learn from teams running millions of requests per day

## Key Features

### 🏷️ Git-like Versioning
```python
prompt_v1 = Prompt(template="Answer: {question}", version="1.0")
prompt_v2 = Prompt(template="Provide detailed answer: {question}", version="2.0")
```

### 📊 Built-in A/B Testing
```python
comparison = compare_prompts(
    prompt_a=prompt_v1,
    prompt_b=prompt_v2,
    test_cases=test_data,
    metric_function=evaluate_response
)
print(f"Winner: {comparison['winner']}")
```

### 🎨 Rich Dashboard Visualization
- Syntax-highlighted prompt templates
- Variable tables with default values
- Version tracking across pipeline runs
- Side-by-side comparison views

## Why This Approach?

Our user research revealed a crucial insight: **teams with millions of daily requests use simple Git-based versioning, not complex management systems.** As one production team noted:

> "There was not one time where someone was like, hey man, I feel like the previous prompt was working so much better"

Instead of backward-looking version management, teams need **forward-looking A/B experimentation**.

## Prerequisites

To follow this guide, you'll need:
- Python environment with ZenML installed
- Basic familiarity with ZenML [pipelines and steps](../../starter-guide/)
- Understanding of [artifacts and materializers](../../starter-guide/manage-artifacts.md)

## Getting Started

The fastest way to understand ZenML's prompt engineering approach is through our practical examples:

1. **Start with the basics**: [30-line prompt engineering example](prompt-engineering-30-loc.md)
2. **Understand the philosophy**: [Why simple versioning works](understanding-prompt-management.md)  
3. **Build real workflows**: [Integration with your existing pipelines](basic-prompt-workflows.md)
4. **Scale with confidence**: [A/B testing and performance tracking](version-control-and-testing.md)

By the end of this guide, you'll have a production-ready approach to prompt engineering that scales from prototypes to millions of requests per day, without the overhead of complex management systems.

Let's start with a simple example that demonstrates all three core features in just 30 lines of code.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>