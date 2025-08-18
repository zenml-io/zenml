## Your First AI Pipeline

Build and evaluate a real AI service powered by a ZenML pipeline. This quickstart works out of the box with a deterministic fallback and upgrades seamlessly to LLMs when you add a provider API key.

### What you'll build
- **Document analysis service**: A FastAPI app that triggers a ZenML pipeline
- **LLM-first with fallback**: Uses LiteLLM if an API key is set, otherwise runs a deterministic analysis
- **Tracked artifacts**: Summary, keywords, sentiment, readability, and rich metadata
- **Quality evaluation**: A separate pipeline that annotates runs and generates an HTML report

### Prerequisites
```bash
pip install "zenml[server]"
zenml init
```

Optional (for LLM mode via LiteLLM, OpenAI shown):
```bash
export OPENAI_API_KEY="your-key"
```

### Get the example
```bash
cd examples/minimal_agent_production
pip install -r requirements.txt
```

### Run the service
```bash
uvicorn app.main:app --reload --port 8010
```

Open `http://localhost:8010` to use the UI, or call it programmatically:
```bash
curl -X POST http://localhost:8010/analyze \
  -H 'Content-Type: application/json' \
  -d '{
        "filename": "sample-report.txt",
        "content": "This is a sample document for analysis...",
        "document_type": "report",
        "analysis_type": "full"
      }'
```

The endpoint triggers a ZenML pipeline run that stores detailed results and metadata you can inspect in the dashboard.

### Inspect your pipeline runs
```bash
zenml up
```

In the dashboard, open the latest run to explore:
- **Steps** like `ingest_document_step`, `analyze_document_step`, `render_report_step`
- **Artifacts** like `DocumentAnalysis` with summary, keywords, sentiment, readability score
- **Metadata** such as latency, token usage, and model name (when in LLM mode)

### Evaluate quality
Generate a quality report across recent analyses:
```bash
python run_evaluation.py
```

Open the run in the dashboard and locate the HTML report artifact with per-item annotations (summary quality, keyword relevance, sentiment accuracy, completeness) and aggregated scores.

### How it works (at a glance)
- The FastAPI app forwards requests to the `document_analysis_pipeline` in `pipelines/production.py`
- The `analyze` step uses LiteLLM if an API key is configured, otherwise a deterministic analyzer
- Artifacts are versioned and traceable; evaluation runs read past analyses and render a report

Key files to explore:
- `examples/minimal_agent_production/pipelines/production.py`
- `examples/minimal_agent_production/steps/analyze.py`
- `examples/minimal_agent_production/run_evaluation.py`

### Production next steps
- **Run remotely**: Configure a remote stack/orchestrator and run the same pipeline on managed compute. See [Deploy](../deploying-zenml/README.md)
- **Automate triggering**: Create a run template (ZenML Pro) and trigger via API/webhooks from your app
- **Operationalize**: Add caching, retries, schedules, and CI/CD using concepts in the docs

### Extend it
- Swap LLMs/providers through LiteLLM without code changes
- Add guardrails/structured outputs via Pydantic models
- Add retrieval or additional steps for more advanced analysis

Looking for the code? Browse the complete example at `examples/minimal_agent_production`.


