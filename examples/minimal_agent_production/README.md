# Document Analysis Pipeline: From Upload to Insights

Transform any document into structured insights with AI-powered analysis - deployed as a production HTTP endpoint.

## 🎯 What You'll Build

This example shows how to create a document analysis system that goes beyond simple text processing. You'll deploy a pipeline that can:

- **Analyze any document**: PDFs, markdown, plain text, or web content
- **Extract structured insights**: Summaries, keywords, sentiment, and readability scores
- **Scale automatically**: Handle multiple requests with built-in caching and error handling
- **Monitor quality**: Built-in evaluation pipeline to track analysis performance over time

### Why Document Analysis vs. Chatbots?

Document analysis is perfect for ZenML pipelines because:

- **Batch-oriented**: Natural fit for pipeline processing paradigms
- **Asynchronous**: Users expect longer processing times for thorough analysis
- **Traceable**: Rich artifacts and metadata for every analysis
- **Evaluatable**: Clear metrics for continuous improvement

## 🚀 Quick Start

### Prerequisites
```bash
pip install "zenml[server]" requests streamlit
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
  "document_type": "text",
  "analysis_type": "full"
}'
```

**Result**: You'll get structured analysis with summary, keywords, sentiment, and readability scores!

### Phase 3: Use the Web Interface

Launch the Streamlit frontend for easy document upload:

```bash
streamlit run streamlit_app.py
```

- **Upload files**: Drag and drop any text document
- **Analyze URLs**: Point to web content for instant analysis  
- **Batch processing**: Analyze multiple documents from file paths

### Phase 4: Monitor and Improve

Run quality evaluation on your analyses:

```bash
python run_evaluation.py
```

This creates detailed reports showing:
- **Summary quality scores**: How well summaries capture key information
- **Keyword relevance**: Whether extracted terms are meaningful
- **Processing metrics**: Speed and token usage over time
- **HTML visualizations**: Rich reports in your ZenML dashboard

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

**Smart fallbacks**: Uses OpenAI/LiteLLM when available, gracefully falls back to rule-based analysis offline.

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

## 📊 Rich Analysis Features

Every document analysis provides:

1. **Smart Summarization**: 2-3 sentence summaries that capture the essence
2. **Keyword Extraction**: Top 5 most relevant terms and phrases  
3. **Sentiment Analysis**: Positive, negative, or neutral classification
4. **Readability Scoring**: 0-1 scale assessment of text complexity
5. **Processing Metrics**: Word count, processing time, and token usage

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
├── static/css/                  # Styling for dashboard reports
├── models.py                    # Pydantic data models
├── streamlit_app.py             # Web interface
└── run_evaluation.py            # Quality assessment CLI
```

## 🎯 Perfect For

- **Content Management**: Automatically categorize and summarize documents
- **Research Analysis**: Process papers, reports, and articles at scale
- **Quality Assessment**: Systematic evaluation of document quality
- **Knowledge Management**: Extract insights from document repositories
- **Compliance Review**: Structured analysis for regulatory requirements

## 🔄 What's Next?

This foundation enables powerful extensions:

- **Multi-language support** with international LLM providers
- **Custom analysis types** for domain-specific insights
- **Automated workflows** triggered by document uploads
- **Integration with document stores** like SharePoint or Google Drive
- **Advanced evaluation metrics** with custom quality rubrics

## 🎯 The Big Picture

This demonstrates ZenML's power for **production AI systems**. Deploy once, scale automatically, monitor continuously - all while maintaining full reproducibility and evaluation capabilities.

---

**Ready to analyze your documents?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams