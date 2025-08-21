# Pydantic AI EDA Pipeline

This example demonstrates how to build an AI-powered Exploratory Data Analysis (EDA) pipeline using **ZenML** and **Pydantic AI**. The pipeline automatically analyzes datasets, generates comprehensive reports, and makes data quality decisions for downstream processing.

## Architecture

```
ingest → eda_agent → quality_gate → routing
```

## Key Features

- **🤖 AI-Powered Analysis**: Uses Pydantic AI with GPT-4 or Claude for intelligent data exploration
- **📊 SQL-Based EDA**: Agent performs analysis through DuckDB SQL queries with safety guards
- **✅ Quality Gates**: Automated data quality assessment with configurable thresholds
- **🌐 Multiple Data Sources**: Support for HuggingFace, local files, and data warehouses
- **📈 Comprehensive Reporting**: Structured JSON reports and human-readable markdown

## What's Included

### Pipeline Steps
- **`ingest_data`**: Load data from HuggingFace, local files, or warehouses
- **`run_eda_agent`**: AI agent performs comprehensive EDA using SQL analysis
- **`evaluate_quality_gate`**: Assess data quality against configurable thresholds
- **`route_based_on_quality`**: Make pipeline routing decisions based on quality

### AI Agent Capabilities
- Statistical analysis and profiling
- Missing data pattern detection
- Correlation analysis
- Outlier identification
- Data quality scoring (0-100)
- Actionable remediation recommendations
- SQL query logging for reproducibility

### CLI Interface
- **Command-line Runner**: Easy execution with various configuration options
- **Quality Assessment**: Quick quality checks without full analysis
- **Multiple Output Formats**: JSON, CSV, and text reporting

## Quick Start

### Prerequisites

```bash
pip install "zenml[server]"
zenml init
```

### Install Dependencies

```bash
git clone https://github.com/zenml-io/zenml.git
cd zenml/examples/pydantic_ai_eda
pip install -r requirements.txt
```

### Set API Keys

```bash
# For OpenAI (recommended)
export OPENAI_API_KEY="your-openai-key"

# Or for Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Quick Example

```bash
# Run simple example
python example.py
```

### CLI Usage

```bash
# Analyze HuggingFace dataset
python run_pipeline.py --source-type hf --source-path "scikit-learn/adult-census-income" --target-column "class"

# Analyze local file
python run_pipeline.py --source-type local --source-path "/path/to/data.csv" --target-column "target"

# Quality-only assessment
python run_quality_check.py --source-path "/path/to/data.csv" --min-quality-score 80
```

## Example Usage

### Python API

```python
from models import DataSourceConfig, AgentConfig
from pipelines.eda_pipeline import eda_pipeline

# Configure data source
source_config = DataSourceConfig(
    source_type="hf",
    source_path="scikit-learn/adult-census-income",
    target_column="class",
    sample_size=10000
)

# Configure AI agent
agent_config = AgentConfig(
    model_name="gpt-5",
    max_tool_calls=50,
    sql_guard_enabled=True
)

# Run pipeline
results = eda_pipeline(
    source_config=source_config,
    agent_config=agent_config,
    min_quality_score=70.0
)

print(f"Quality Score: {results['quality_decision'].quality_score}")
print(f"Quality Gate: {'PASSED' if results['quality_decision'].passed else 'FAILED'}")
```

## Pipeline Configuration

### Data Sources

**HuggingFace Datasets:**
```python
source_config = DataSourceConfig(
    source_type="hf",
    source_path="scikit-learn/adult-census-income",
    sampling_strategy="random",
    sample_size=50000
)
```

**Local Files:**
```python
source_config = DataSourceConfig(
    source_type="local",
    source_path="/path/to/data.csv",
    target_column="target"
)
```

**Data Warehouses:**
```python
source_config = DataSourceConfig(
    source_type="warehouse",
    source_path="SELECT * FROM customer_data LIMIT 100000",
    warehouse_config={
        "type": "bigquery",
        "project_id": "my-project"
    }
)
```

### AI Agent Configuration

```python
agent_config = AgentConfig(
    model_name="gpt-5",  # or "claude-4"
    max_tool_calls=100,
    sql_guard_enabled=True,
    preview_limit=20,
    timeout_seconds=600
)
```

### Quality Gate Thresholds

```python
quality_decision = evaluate_quality_gate(
    report_json=report,
    min_quality_score=75.0,
    block_on_high_severity=True,
    max_missing_data_pct=25.0,
    require_target_column=True
)
```

## Analysis Outputs

### EDA Report Structure
```json
{
  "headline": "Dataset contains 32,561 rows with moderate data quality issues",
  "key_findings": [
    "Found 6 numeric columns suitable for quantitative analysis",
    "Missing data is 7.3% overall, within acceptable range",
    "Strong correlation detected between age and hours-per-week (0.89)"
  ],
  "risks": ["Potential class imbalance in target variable"],
  "fixes": [
    {
      "title": "Address missing values in workclass column",
      "severity": "medium",
      "code_snippet": "df['workclass'].fillna(df['workclass'].mode()[0])",
      "estimated_impact": 0.15
    }
  ],
  "data_quality_score": 78.5,
  "correlation_insights": [...],
  "missing_data_analysis": {...}
}
```

### Quality Gate Decision
```json
{
  "passed": true,
  "quality_score": 78.5,
  "decision_reason": "All quality checks passed",
  "blocking_issues": [],
  "recommendations": [
    "Data quality is acceptable for downstream processing",
    "Consider implementing monitoring for quality regression"
  ]
}
```

## Data Security

### Quality Configuration
```python
# Configure quality thresholds
results = eda_pipeline(
    source_config=source_config,
    min_quality_score=80.0,
    max_missing_data_pct=15.0
)
```

### SQL Safety Guards
- Only `SELECT` and `WITH` statements allowed
- Prohibited operations: `DROP`, `DELETE`, `INSERT`, `UPDATE`
- Auto-injection of `LIMIT` clauses for large result sets
- Query logging for full auditability

## Production Deployment

### Remote Orchestration
```python
# Configure ZenML stack for cloud deployment
zenml stack register remote_stack \
  --orchestrator=kubernetes \
  --artifact_store=s3 \
  --container_registry=ecr

# Run with remote stack
zenml stack set remote_stack
python run_pipeline.py --source-path "s3://my-bucket/data.parquet"
```

### Monitoring & Alerts
- Pipeline execution tracking via ZenML dashboard
- Quality gate failure notifications
- Data drift detection capabilities
- Token usage and cost monitoring

## Examples Gallery

### Customer Segmentation Analysis
```bash
python run_pipeline.py \
  --source-type hf \
  --source-path "scikit-learn/adult-census-income" \
  --target-column "class" \
  --min-quality-score 80
```

### Financial Risk Assessment
```bash
python run_pipeline.py \
  --source-type local \
  --source-path "financial_data.csv" \
  --min-quality-score 90 \
  --require-target-column \
  --target-column "risk_score"
```

### Time Series Data Quality Check
```bash
python run_quality_check.py \
  --source-path "time_series.parquet" \
  --max-missing-data-pct 10 \
  --require-target-column \
  --target-column "value"
```

## Advanced Features

### Custom Data Warehouses
Support for BigQuery, Snowflake, Redshift, and generic SQL connections.

### Multi-Model Analysis
Switch between OpenAI GPT-4, Anthropic Claude, and other providers.

### Pipeline Caching
Automatic caching of expensive operations for faster iterations.

### Artifact Lineage
Full traceability of data transformations and analysis steps.

## Troubleshooting

### Common Issues

**Missing API Keys:**
```bash
export OPENAI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"
```

**DuckDB Import Errors:**
```bash
pip install duckdb>=1.0.0
```

**Pydantic AI Installation:**
```bash
pip install pydantic-ai>=0.0.13
```

**Large Dataset Memory Issues:**
- Reduce `sample_size` in DataSourceConfig
- Use `enable_masking=True` to reduce memory footprint
- Consider using `quality_only_pipeline` for quick checks

### Performance Optimization

- Use `gpt-4o-mini` instead of `gpt-5` for faster analysis
- Limit `max_tool_calls` for time-constrained scenarios
- Enable snapshot caching for repeated analysis
- Use stratified sampling for large datasets

## Contributing

This example demonstrates the integration patterns between ZenML and Pydantic AI. Contributions for additional data sources, quality checks, and analysis capabilities are welcome.

## License

This example is part of the ZenML project and follows the Apache 2.0 license.