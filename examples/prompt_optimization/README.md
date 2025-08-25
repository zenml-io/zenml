# Prompt Optimization with ZenML

This example demonstrates **ZenML's artifact management** through a two-stage AI prompt optimization workflow using **Pydantic AI** for exploratory data analysis.

## What This Example Shows

**Stage 1: Prompt Optimization**
- Tests multiple prompt variants against sample data
- Compares performance using data quality scores and execution time
- Tags the best-performing prompt with an **exclusive ZenML tag**
- Stores the optimized prompt in ZenML's artifact registry

**Stage 2: Production Analysis**
- Automatically retrieves the tagged optimal prompt from the registry
- Runs production EDA analysis using the best prompt
- Demonstrates real artifact sharing between pipeline runs

This showcases how ZenML enables **reproducible ML workflows** where optimization results automatically flow into production systems.

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

```bash
# Model selection
python run.py --model-name "gpt-4o-mini"
python run.py --model-name "claude-3-haiku-20240307"

# Performance tuning
python run.py --max-tool-calls 8 --timeout-seconds 120

# Development options
python run.py --no-cache  # Disable caching for fresh runs
```

## Expected Output

When you run the complete workflow, you'll see:

1. **Optimization Stage**: Testing of 3 prompt variants with performance metrics
2. **Tagging**: Best prompt automatically tagged in ZenML registry  
3. **Production Stage**: Retrieval and use of optimized prompt
4. **Results**: EDA analysis with data quality scores and recommendations

The ZenML dashboard will show the complete lineage from optimization to production use.

## Next Steps

- **View Results**: Check the ZenML dashboard for pipeline runs and artifacts
- **Customize Prompts**: Modify the prompt variants in `run.py` for your domain
- **Scale Up**: Deploy with remote orchestrators for production workloads
- **Integrate**: Connect to your existing data sources and ML pipelines