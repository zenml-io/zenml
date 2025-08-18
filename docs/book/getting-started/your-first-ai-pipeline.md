---
description: Build your first AI pipeline and service with ZenML in minutes.
icon: rocket
---

## Your First AI Pipeline

Build and evaluate a real AI service powered by a ZenML pipeline. This quickstart works out of the box with a deterministic fallback and upgrades seamlessly to LLMs when you add a provider API key.

{% hint style="info" %}
Why pipelines?
- **Reproducible & portable**: Run the same code locally or on the cloud by switching stacks.
- **One approach for models and agents**: Steps, pipelines, and artifacts work for sklearn and LLMs alike.
- **Evaluate & observe by default**: Quality reports, lineage, and step metadata (tokens, latency) out of the box.
{% endhint %}

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

<figure>
  <img src="../.gitbook/assets/your-first-ai-pipeline-app.png" alt="FastAPI document analysis UI">
  <figcaption>The web UI served by uvicorn at <code>http://localhost:8010</code>.</figcaption>
</figure>

### Inspect your pipeline runs
```bash
zenml login --local
```

In the dashboard, open the latest run to explore:
- **Steps** like `ingest_document_step`, `analyze_document_step`, `render_report_step`
- **Artifacts** like `DocumentAnalysis` with summary, keywords, sentiment, readability score
- **Metadata** such as latency, token usage, and model name (when in LLM mode)

<figure>
  <img src="../.gitbook/assets/your-first-ai-pipeline-dag-analysis.png" alt="Document analysis pipeline DAG in ZenML dashboard">
  <figcaption>Document analysis pipeline DAG with step-level artifacts and metadata.</figcaption>
</figure>

### Evaluate quality
Generate a quality report across recent analyses:
```bash
python run_evaluation.py
```

Open the run in the dashboard and locate the HTML report artifact with per-item annotations (summary quality, keyword relevance, sentiment accuracy, completeness) and aggregated scores.

<figure>
  <img src="../.gitbook/assets/your-first-ai-pipeline-dag-evaluation.png" alt="Evaluation pipeline DAG in ZenML dashboard">
  <figcaption>Evaluation pipeline producing an HTML report artifact with aggregated metrics.</figcaption>
</figure>

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

### Architecture (at a glance)
```mermaid
graph TD
  U[User / Client] --> A[FastAPI app]
  A --> P[ZenML document analysis pipeline]
  P --> S1[ingest_document_step]
  S1 --> S2[analyze_document_step (LLM or fallback)]
  S2 --> S3[render_report_step]
  S2 -->|DocumentAnalysis artifact| AR[Artifact Store]
  S3 -->|HTML Report| AR

  subgraph Evaluation
    E[Evaluation pipeline] --> R1[load recent analyses]
    R1 --> R2[annotate & score]
    R2 --> R3[render evaluation HTML]
    R3 --> AR
  end

  classDef dim fill:#f5f5f7,stroke:#d0d0d7,color:#333;
  class Evaluation dim;

  %% Optional remote execution
  P -. runs on .-> O[(Orchestrator: local or remote)]
  O -. stores .-> AR
```


