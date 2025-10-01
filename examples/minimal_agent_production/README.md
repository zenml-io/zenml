# Deploying agents with ZenML: Document Analysis Pipeline

This example shows how to build and deploy an **LLM‑powered document analysis** workflow as a **production HTTP endpoint** using ZenML. You’ll get structured insights (summary, keywords, sentiment, readability) from text‑like inputs, and an optional Streamlit UI to interact with the deployment.

## 🎯 What You’ll Build

A deployed pipeline that:

- **Ingests text** from direct input, local files, or URLs (HTML is lightly cleaned)
- **Extracts structured insights**: summary, top keywords, sentiment, readability
- **Runs online or offline**: uses OpenAI if `OPENAI_API_KEY` is set, otherwise a rule‑based fallback
- **Surfaces metrics**: word count, latency, token usage (when in LLM mode)
- **Returns an HTML report** for the ZenML dashboard

> ℹ️ **Scope**: Out‑of‑the‑box input types are text/markdown/code and simple web pages. PDF parsing is **not** included by default.

## 🚀 Get Started

### Prerequisites

```bash
pip install "zenml[server]"
export OPENAI_API_KEY=sk-xxx   # Optional: if absent, the pipeline falls back to a deterministic analyzer
````

### Setup

```bash
git clone --depth 1 https://github.com/zenml-io/zenml.git
cd zenml/examples/minimal_agent_production
pip install -r requirements.txt
zenml init
```

### Phase 1: Deploy the Analysis Pipeline

Deploy the pipeline as a managed HTTP endpoint:

```bash
zenml pipeline deploy pipelines.doc_analyzer.doc_analyzer
```

Find your endpoint URL:

```bash
zenml deployment describe doc_analyzer
```

### Phase 2: Analyze a Document

#### Use the ZenML CLI

```bash
zenml deployment invoke doc_analyzer \
  --content="Artificial Intelligence is transforming how we work..." \
  --filename="ai-overview.txt" \
  --document_type="text"
```

#### Call the HTTP endpoint directly

If you prefer `curl`/`requests`, send a JSON body with **parameters**:

```bash
ENDPOINT=http://localhost:8000   # replace with your deployment URL
curl -X POST "$ENDPOINT/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "content": "Your text here...",
      "filename": "document.txt",
      "document_type": "text"
    }
  }'
```

If your deployment requires auth, include:

```bash
-H "Authorization: Bearer <YOUR_KEY>"
```

### Phase 3: Use the Web Interface (optional)

![Streamlit app interface](../../docs/book/.gitbook/assets/minimal_agent_production_streamlit.png)

Launch the Streamlit frontend:

```bash
streamlit run streamlit_app.py
```

Enter the endpoint URL (e.g., `http://localhost:8000`) and optionally an auth key.

## 🤖 How It Works

The pipeline orchestrates three steps:

```python
@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def doc_analyzer(content=None, url=None, path=None, filename=None, document_type="text"):
    document = ingest_document_step(content, url, path, filename, document_type)
    analysis = analyze_document_step(document)          # OpenAI or deterministic fallback
    render_analysis_report_step(analysis)               # HTML report for the dashboard
    return analysis
```

* **LLM path**: When `OPENAI_API_KEY` is present, `analyze_document_step` calls OpenAI chat completions and parses a structured JSON response.
* **Fallback path**: A rule‑based analyzer produces a summary, keywords, and readability without external calls.

## 🔧 Production Notes

The pipeline comes pre-configured with Docker settings in `pipelines/doc_analyzer.py`:

```python
docker_settings = DockerSettings(
    requirements="requirements.txt",
    environment={"OPENAI_API_KEY": "${OPENAI_API_KEY}"},
)
```

These settings are automatically applied when you deploy. If you need to override settings or add deployer-specific options (like authentication), create a YAML config file:

```yaml
# my_config.yaml (optional)
settings:
  deployer:
    generate_auth_key: true
```

Then deploy with:

```bash
zenml pipeline deploy pipelines.doc_analyzer.doc_analyzer --config my_config.yaml
```

> Scaling & concurrency options vary by orchestrator/deployment target; consult the ZenML deployment docs for deployment configuration options.

## 📁 Project Structure

```
examples/minimal_agent_production/
├── pipelines/
│   └── doc_analyzer.py          # Pipeline definition and Docker settings
├── steps/
│   ├── analyze.py               # LLM analysis + deterministic fallback
│   ├── ingest.py                # Text/URL/path ingestion
│   ├── render.py                # HTML report renderer
│   ├── utils.py                 # Text cleaning & heuristics
│   └── templates/
│       ├── report.css           # Report styling
│       └── report.html          # Report template
├── constants.py                  # Tunables & UI constants
├── models.py                     # Pydantic models for I/O
├── prompts.py                    # LLM prompt builder
├── requirements.txt              # Extra deps (OpenAI, Streamlit)
└── streamlit_app.py              # Optional web UI client
```

## 🎯 The Big Picture

This is the same **steps → pipeline → artifacts** pattern you use for classic ML, now applied to an LLM workflow. You get deployable endpoints, reproducibility, and dashboard artifacts without building a bespoke web service.

---

**Ready to analyze your documents?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams
