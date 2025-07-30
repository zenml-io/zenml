# Prompt Engineering Example

A minimal example demonstrating ZenML's prompt engineering capabilities through a simple A/B comparison workflow.

## Features Demonstrated

✅ **Simple Versioning**: Git-like version numbers (v1.0, v2.0)  
✅ **A/B Testing**: Compare prompt variants automatically  
✅ **Dashboard Integration**: Rich visualizations without setup  

## Project Structure

```
prompt_engineering/
├── pipelines/
│   └── simple_comparison.py    # Main comparison pipeline
├── steps/
│   ├── prompt_creation.py      # Step for creating prompt versions
│   └── prompt_testing.py       # Step for A/B testing prompts
├── utils/
│   └── helpers.py              # Utility functions
├── run_simple_comparison.py    # Main script to run example
└── README.md                   # This file
```

## Quick Start

1. **Run the example**:
   ```bash
   cd examples/prompt_engineering
   python run_simple_comparison.py
   ```

2. **Check your dashboard**:
   - Navigate to your ZenML dashboard
   - View the pipeline run
   - See prompt artifacts with rich visualizations
   - Compare v1.0 vs v2.0 results

## What Happens

1. **Create Versions**: Two prompt versions are created:
   - v1.0: `"Answer: {question}"`
   - v2.0: `"Please provide a detailed answer: {question}"`

2. **A/B Test**: Both prompts are tested against sample questions

3. **Determine Winner**: Simple scoring determines which prompt performs better

4. **Dashboard View**: All prompts and results appear as artifacts with rich visualizations

## Extending the Example

Replace the simple length-based scoring in `steps/prompt_testing.py` with:
- Real LLM evaluation
- Human feedback scores
- Domain-specific metrics
- Statistical significance testing

The structure scales from this simple example to production workflows handling millions of requests.