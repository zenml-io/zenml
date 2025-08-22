# Pydantic AI EDA Pipeline

AI-powered Exploratory Data Analysis pipeline using **ZenML** and **Pydantic AI**. Automatically analyzes datasets, generates reports, and makes quality decisions for downstream processing.

## Architecture

```
ingest_data → run_eda_agent → evaluate_quality_gate_with_routing
```

## Features

- 🤖 **AI-Powered Analysis** with GPT-4/Claude
- 📊 **SQL-Based EDA** through DuckDB with safety guards  
- ✅ **Quality Gates** with configurable thresholds
- 🌐 **Multiple Data Sources** (HuggingFace, local files, warehouses)
- 📈 **Comprehensive Reporting** (JSON/markdown)

## Quick Start

```bash
# Install
pip install "zenml[server]" && zenml init
cd zenml/examples/pydantic_ai_eda && pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="your-openai-key"  # or ANTHROPIC_API_KEY

# Run examples  
python run.py
python run_prompt_experiment.py
```

## Usage

```python
from models import DataSourceConfig, AgentConfig
from pipelines.eda_pipeline import eda_pipeline

# EDA Analysis
source_config = DataSourceConfig(
    source_type="local",
    source_path="iris_dataset.csv", 
    target_column="species"
)

results = eda_pipeline(source_config=source_config)

# Prompt Experimentation  
from pipelines.prompt_experiment_pipeline import prompt_experiment_pipeline

prompts = ["Analyze this data", "Provide detailed insights"]
experiment = prompt_experiment_pipeline(
    source_config=source_config, 
    prompt_variants=prompts
)
```

## Output

The pipeline generates:
- **EDA Report**: Statistical analysis, correlations, missing data patterns, quality score (0-100)
- **Quality Gate**: Pass/fail decision with recommendations
- **Remediation**: Actionable code snippets for data issues

## Security & Production

- **SQL Safety**: Only SELECT/WITH queries allowed, auto-LIMIT injection
- **Remote Orchestration**: Kubernetes, S3, ECR support via ZenML stacks
- **Monitoring**: Pipeline tracking, quality alerts, cost monitoring

## Troubleshooting

```bash
# Common fixes
pip install duckdb>=1.0.0 pydantic-ai>=0.0.13
export OPENAI_API_KEY="your-key"

# Performance: use gpt-4o-mini, reduce sample_size for large datasets
```