# Prompt Optimization with ZenML

This example demonstrates **ZenML's artifact management** through a two-stage AI prompt optimization workflow using **Pydantic AI** for exploratory data analysis.

## What This Example Shows

**Stage 1: Prompt Optimization**
- Tests multiple prompt variants against sample data
- Compares performance using data quality scores and execution time
- Emits a scoreboard artifact that summarizes quality, speed, findings, and success per prompt
- Tags the best-performing prompt with an **exclusive ZenML tag**
- Stores the optimized prompt in ZenML's artifact registry

**Stage 2: Production Analysis**
- Automatically attempts to retrieve the latest optimized prompt from the registry
- Falls back to the default system prompt if no optimized prompt is available or retrieval fails
- Runs production EDA analysis using the selected prompt
- Returns a `used_optimized_prompt` boolean to indicate whether the optimized prompt was actually used
- Demonstrates real artifact sharing between pipeline runs

This showcases how ZenML enables **reproducible ML workflows** where optimization results automatically flow into production systems, with safe fallbacks.

## Quick Start

### Prerequisites
```bash
# Install ZenML and initialize
pip install "zenml[server]"
zenml init

# Install example dependencies  
pip install -r requirements.txt

# Set your API key (OpenAI or Anthropic)
export OPENAI_API_KEY="your-openai-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Run the Example
```bash
# Complete two-stage workflow (default behavior)
python run.py

# Run individual stages
python run.py --optimization-pipeline    # Stage 1: Find best prompt
python run.py --production-pipeline      # Stage 2: Use optimized prompt

# Force a specific provider/model (override auto-detection)
python run.py --provider openai --model-name gpt-4o-mini
python run.py --provider anthropic --model-name claude-3-haiku-20240307
```

## Data Sources

The example supports multiple data sources:

```bash
# HuggingFace datasets (default)
python run.py --data-source "hf:scikit-learn/iris"
python run.py --data-source "hf:scikit-learn/wine" 

# Local CSV files
python run.py --data-source "local:./my_data.csv"

# Specify target column
python run.py --data-source "local:sales.csv" --target-column "revenue"

# Sample a subset of rows for faster iterations
python run.py --data-source "hf:scikit-learn/iris" --sample-size 500
```

## Key ZenML Concepts Demonstrated

### Artifact Management
- **Exclusive Tagging**: Only one prompt can have the "optimized" tag at a time
- **Artifact Registry**: Centralized storage for ML artifacts with versioning
- **Cross-Pipeline Sharing**: Production pipeline automatically finds optimization results

### Pipeline Orchestration
- **Multi-Stage Workflows**: Optimization → Production with artifact passing
- **Conditional Execution**: Production pipeline adapts based on available artifacts
- **Lineage Tracking**: Full traceability from prompt testing to production use

### AI Integration
- **Model Flexibility**: Works with OpenAI GPT or Anthropic Claude models
- **Performance Testing**: Systematic comparison of prompt variants
- **Production Deployment**: Seamless transition from experimentation to production

## Configuration Options

### Provider and Model Selection
```bash
# Auto (default): infer provider from model name or environment keys
python run.py

# Force provider explicitly
python run.py --provider openai --model-name gpt-4o-mini
python run.py --provider anthropic --model-name claude-3-haiku-20240307

# Fully-qualified model names are also supported
python run.py --model-name "openai:gpt-4o-mini"
python run.py --model-name "anthropic:claude-3-haiku-20240307"
```

### Scoring Configuration
Configure how prompts are ranked during optimization:
```bash
# Weights for the aggregate score
python run.py --weight-quality 0.7 --weight-speed 0.2 --weight-findings 0.1

# Speed penalty (points per second) applied to compute a speed score
python run.py --speed-penalty-per-second 2.0

# Findings scoring (base points per finding) and cap
python run.py --findings-score-per-item 0.5 --findings-cap 20
```

*Why a cap?* It prevents a variant that simply emits an excessively long list of "findings" from dominating the overall score. Capping keeps the aggregate score bounded and comparable across variants while still rewarding useful coverage.

### Custom Prompt Files
Provide your own prompt variants via a file (UTF-8, one prompt per line; blank lines ignored):
```bash
python run.py --prompts-file ./my_prompts.txt
```

### Sampling
Downsample large datasets to speed up experiments:
```bash
python run.py --sample-size 500
```

### Budgets and Timeouts
Budgets are enforced at the tool boundary for deterministic behavior and cost control:
```bash
# Tool-call budget and overall time budget for the agent
python run.py --max-tool-calls 8 --timeout-seconds 120
```
- The agent tools check and enforce these budgets during execution.

### Caching
```bash
# Disable caching for fresh runs
python run.py --no-cache
```

## Expected Output

When you run the complete workflow, you'll see:

1. **Optimization Stage**: Testing of multiple prompt variants with performance metrics
2. **Scoreboard**: CLI prints a compact top-3 summary (score, time, findings, success) and a short preview of the best prompt; a full scoreboard artifact is saved
3. **Tagging**: Best prompt automatically tagged in ZenML registry (exclusive "optimized" tag)
4. **Production Stage**: Retrieval and use of optimized prompt if available; otherwise falls back to the default
5. **Results**: EDA analysis with data quality scores and recommendations, plus a `used_optimized_prompt` flag indicating whether an optimized prompt was actually used

The ZenML dashboard will show the complete lineage from optimization to production use, including the prompt scoreboard and tagged best prompt.

## Next Steps

- **View Results**: Check the ZenML dashboard for pipeline runs and artifacts
- **Customize Prompts**: Provide your own variants via `--prompts-file`
- **Tune Scoring**: Adjust weights and penalties to match your evaluation criteria
- **Scale Up**: Deploy with remote orchestrators for production workloads
- **Integrate**: Connect to your existing data sources and ML pipelines