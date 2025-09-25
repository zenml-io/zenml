# Deploying agents with ZenML: Document Analysis Pipeline

ZenML can be used to develop and deploy agents or LLM-powered workflows. This example use-case
transforms any document into structured insights with AI-powered analysis - deployed as a production HTTP endpoint.

## 🎯 What You'll Build

This example shows how to create a document analysis system with ZenML. You'll deploy a pipeline that can:

- **Analyze any document**: PDFs, markdown, plain text, or web content
- **Extract structured insights**: Summaries, keywords, sentiment, and readability scores
- **Scale automatically**: Handle multiple requests with built-in caching and error handling
- **Monitor quality**: Built-in evaluation pipeline to track analysis performance over time

Every document analysis provides:

1. **Smart Summarization**: 2-3 sentence summaries that capture the essence
2. **Keyword Extraction**: Top 5 most relevant terms and phrases  
3. **Sentiment Analysis**: Positive, negative, or neutral classification
4. **Readability Scoring**: 0-1 scale assessment of text complexity
5. **Processing Metrics**: Word count, processing time, and token usage

The key insight in this example is that you can use the same pipeline principles that are used
in "normal" batch pipelines written in ZenML, and deploy it as a real-time agentic endpoint.

This avoids the complexity of having to create a bespoke FastAPI endpoint, and add all the monitoring
overhead that results in productionalizing agents.

## 🚀 Get Started

### Prerequisites
```bash
pip install "zenml[servers]" requests streamlit
export OPENAI_API_KEY=sk-xxx  # Optional - works offline without it
```

### Setup
```bash
git clone --depth 1 https://github.com/zenml-io/zenml.git
cd zenml/examples/minimal_agent_production
pip install -r requirements.txt
zenml init
```

### Phase 1: Deploy Your Analysis Pipeline

Deploy the document analysis pipeline as a REST API:

```bash
zenml pipeline deploy pipelines.doc_analyzer.doc_analyzer
```

Get your endpoint URL:
```bash
zenml deployment describe doc-analyzer
```

### Phase 2: Analyze Your First Document

**Quick test with CLI:**
```bash
zenml deployment invoke doc-analyzer --json '{
  "content": "Artificial Intelligence is transforming how we work. Machine learning models can now process vast amounts of data to extract meaningful insights, helping businesses make better decisions faster than ever before.",
  "filename": "ai-overview.txt",
  "document_type": "text"
}'
```

**Result**: You'll get structured analysis with summary, keywords, sentiment, and readability scores!

### Phase 3: Use the Web Interface

Launch the Streamlit frontend for easy document upload:

```bash
streamlit run streamlit_app.py
```

## 🤖 How It Works

The pipeline intelligently handles different input types:

```python
@pipeline
def document_analysis_pipeline(
    content: Optional[str] = None,
    url: Optional[str] = None, 
    path: Optional[str] = None,
    # ... other params
):
    document = ingest_document_step(content, url, path)  # Smart ingestion
    analysis = analyze_document_step(document)          # AI analysis
    report = render_analysis_report_step(analysis)      # Rich visualization
    return analysis
```

**Smart fallbacks**: Uses OpenAI when available, gracefully falls back to rule-based analysis offline.

## 🏗️ Multiple Ways to Analyze

### Direct Content
Perfect for real-time text processing:
```bash
zenml deployment invoke doc-analyzer --json '{
  "content": "Your document text here...",
  "document_type": "text"
}'
```

### URL Analysis
Great for processing web content:
```bash
zenml deployment invoke doc-analyzer --json '{
  "url": "https://example.com/article.html",
  "document_type": "article"
}'
```

### File Path Processing
Ideal for batch processing stored documents:
```bash
zenml deployment invoke doc-analyzer --json '{
  "path": "documents/report.md",
  "document_type": "markdown"
}'
```


## 🔧 Production Configuration

For production deployments, create a config file:

```yaml
# production.yaml
settings:
  docker:
    requirements: requirements.txt
    python_package_installer: uv
  resources:
    memory: "2GB"
    cpu_count: 2
    min_replicas: 1
    max_replicas: 5
    max_concurrency: 10
  deployer:
    generate_auth_key: true
```

Deploy with production settings:
```bash
zenml pipeline deploy pipelines.doc_analyzer.doc_analyzer \
  --config production.yaml
```

## 📁 Project Structure

```
examples/minimal_agent_production/
├── pipelines/
│   └── doc_analyzer.py          # Main document analysis pipeline
├── steps/
│   ├── analyze.py               # AI analysis with smart fallbacks
│   ├── ingest.py                # Multi-source document ingestion
│   ├── render.py                # Rich HTML report generation
│   ├── evaluate.py              # Quality scoring and metrics
│   └── utils.py                 # Text processing utilities
├── models.py                    # Pydantic data models
├── streamlit_app.py             # Web interface
└── run_evaluation.py            # Quality assessment CLI
```

## 🎯 The Big Picture

This demonstrates ZenML's power for **production AI systems**. Deploy once, scale automatically, monitor continuously - all while maintaining full reproducibility and evaluation capabilities.

---

**Ready to analyze your documents?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams