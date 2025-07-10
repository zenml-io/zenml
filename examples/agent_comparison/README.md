# Agent Architecture Comparison Pipeline

This example demonstrates how to use ZenML to compare different AI agent architectures in a reproducible, data-driven way. It showcases the unified MLOps approach for both traditional ML models and modern AI agents.

## 🎯 What This Example Demonstrates

- **Multi-Architecture Agent Comparison**: Compare three different customer service agent approaches
- **Traditional ML Integration**: Train a scikit-learn intent classifier alongside AI agents
- **LangGraph Workflow**: Implement a real [LangGraph](https://www.langchain.com/langgraph) agent with structured workflow
- **LiteLLM Integration**: Use [LiteLLM](https://litellm.ai/) for unified access to 100+ LLM providers (OpenAI, Anthropic, Groq, etc.)
- **Smart LLM Fallbacks**: Automatically use real LLMs when API keys are available, fall back to mock responses otherwise
- **Rich Visualizations**: Generate HTML reports and Mermaid diagrams for the ZenML dashboard
- **Reproducible AI Evaluation**: Apply MLOps principles to agent development

## 🏗️ Architecture Overview

The pipeline implements three agent architectures:

1. **SingleAgentRAG**: Simple RAG agent handling all queries with one approach
2. **MultiSpecialistAgents**: Multiple specialized agents for different query types  
3. **LangGraphCustomerServiceAgent**: LangGraph-based workflow with structured steps:

```
START → analyze_query → classify_intent → generate_response → validate_response → END
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install ZenML with required integrations
pip install "zenml[server]"

# Initialize ZenML
zenml init
```

### Optional: Enable Real LLM Calls

The pipeline automatically detects API keys and uses real LLMs when available:

```bash
# For OpenAI (recommended)
export OPENAI_API_KEY="your-api-key-here"

# Or use other providers supported by LiteLLM
export ANTHROPIC_API_KEY="your-anthropic-key"
export GROQ_API_KEY="your-groq-key"
export COHERE_API_KEY="your-cohere-key"

# Without API keys, the pipeline uses mock responses (perfect for demos!)
```

### Run the Pipeline

```bash
# Clone and navigate to the example
cd examples/agent_comparison

# Install dependencies
pip install -r requirements.txt

# Run the comparison pipeline
python agent_comparison_pipeline.py
```

### View Results

```bash
# Start the ZenML dashboard
zenml login

# Navigate to your pipeline run to see:
# - Customer service queries dataset
# - Trained intent classifier model  
# - Architecture performance metrics
# - Interactive Mermaid workflow diagram
# - Beautiful HTML comparison report
```

## 📁 Project Structure

The example has been refactored into a clean modular structure:

```
examples/agent_comparison/
├── agents.py                    # Agent architecture implementations
├── llm_utils.py                # LLM utilities and fallback logic
├── steps/                      # ZenML pipeline steps
│   ├── __init__.py
│   ├── data_loading.py         # Load customer service data
│   ├── model_training.py       # Train intent classifier
│   ├── testing.py              # Run architecture comparison
│   └── evaluation.py           # Generate evaluation report
├── pipelines/                  # ZenML pipelines
│   ├── __init__.py
│   └── agent_comparison.py     # Main comparison pipeline
├── agent_comparison_pipeline.py # Main entry point
├── run.py                      # Simple runner script
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## 📊 Pipeline Steps

### 1. Load Customer Service Data
```python
@step
def load_real_conversations() -> Annotated[pd.DataFrame, "customer_service_queries"]:
    # Loads 15 sample customer service queries with varying complexity
```

### 2. Train Intent Classifier
```python
@step  
def train_intent_classifier(queries: pd.DataFrame) -> Annotated[BaseEstimator, "intent_classifier_model"]:
    # Trains a scikit-learn pipeline (TF-IDF + LogisticRegression)
    # Classifies queries into: returns, billing, shipping, warranty, general
```

### 3. Run Architecture Comparison
```python
@step
def run_architecture_comparison(
    queries: pd.DataFrame, 
    intent_classifier: BaseEstimator
) -> Tuple[Dict, HTMLString]:
    # Tests all three architectures on the same data
    # Returns performance metrics and LangGraph Mermaid diagram
```

### 4. Generate Evaluation Report
```python
@step
def evaluate_and_decide(
    queries: pd.DataFrame, 
    results: Dict
) -> Annotated[HTMLString, "architecture_comparison_report"]:
    # Creates beautiful HTML report with winner selection and recommendations
```

## 🎨 Visualization Features

- **Mermaid Workflow Diagram**: Interactive visualization of the LangGraph agent workflow
- **HTML Performance Report**: Styled comparison with metrics, recommendations, and next steps
- **ZenML Dashboard Integration**: All artifacts are beautifully rendered in the dashboard

## 🔧 Customization

### Add Your Own Agent Architecture

```python
class YourCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__("YourCustomAgent")
    
    def process_query(self, query: str) -> AgentResponse:
        # Your implementation here
        return AgentResponse(text="...", latency_ms=..., confidence=..., tokens_used=...)

# Add to the architectures dictionary in run_architecture_comparison()
```

### Modify Evaluation Metrics

Edit the `evaluate_and_decide` step to add custom metrics:

```python
# Add your custom metrics
custom_metric = calculate_your_metric(responses)
metrics["custom_score"] = custom_metric

# Adjust the overall score calculation
overall_score = (
    metrics["avg_confidence"] * 0.3 +
    metrics["custom_score"] * 0.2 +
    # ... other metrics
)
```

### LiteLLM Integration

The pipeline automatically uses real LLMs when API keys are detected:

```python
# The pipeline uses LiteLLM for unified access to 100+ providers
from litellm import completion

# This works with any provider supported by LiteLLM:
response = completion(
    model="gpt-3.5-turbo",  # OpenAI
    # model="claude-3-sonnet",  # Anthropic  
    # model="groq/llama2-70b-4096",  # Groq
    # model="command-r",  # Cohere
    messages=[{"role": "user", "content": query}],
    max_tokens=200
)
```

**Supported Providers via LiteLLM:**
- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Groq**: `groq/llama2-70b-4096`, `groq/mixtral-8x7b-32768`
- **Cohere**: `command-r`, `command-r-plus`
- **100+ other providers** - see [LiteLLM docs](https://docs.litellm.ai/docs/providers)

## 📚 Key Concepts Demonstrated

- **Unified MLOps**: Same framework for traditional ML and AI agents
- **Reproducible AI**: Version control for prompts, models, and agent configurations  
- **Data-Driven Decisions**: Systematic evaluation rather than subjective choices
- **Pipeline Orchestration**: Structured workflows with proper dependencies
- **Artifact Tracking**: All inputs, outputs, and metadata automatically logged
- **Visualization**: Rich HTML and interactive diagrams in the dashboard

## 🌐 LLM Ecosystem Integration

This example demonstrates ZenML's seamless integration with the modern AI landscape:

### 🔗 **LangGraph** - Structured Agent Workflows
- Build complex, multi-step agent workflows with full observability
- Each workflow step is tracked and versioned by ZenML
- Interactive Mermaid diagrams show your agent's decision flow

### ⚡ **LiteLLM** - Universal LLM Access  
- Single interface to 100+ LLM providers (OpenAI, Anthropic, Groq, Cohere, etc.)
- Automatic fallbacks and smart provider switching
- Cost and performance tracking across different models

### 🤝 Integration Points

This example shows how to integrate:
- **LangGraph**: For structured agent workflows with full lineage tracking
- **LiteLLM**: For unified access to the entire LLM ecosystem
- **scikit-learn**: For traditional ML components alongside AI agents
- **ZenML**: For orchestration, versioning, and artifact tracking
- **HTML/Mermaid**: For rich visualizations and interactive diagrams

**The Result**: A unified MLOps approach that works for everything from decision trees to complex agent workflows, all integrated with the tools you already use.

## 🎯 Production Readiness

To make this production-ready:

1. **Add Real Data Sources**: Replace sample data with your actual customer queries
2. **Implement Real LLMs**: Connect to OpenAI, Anthropic, or other LLM providers
3. **Add More Metrics**: Include cost tracking, customer satisfaction scores, etc.
4. **Scale Testing**: Run on larger datasets and more architectures
5. **Add Monitoring**: Track performance degradation over time
6. **Implement A/B Testing**: Gradually roll out winning architectures

## 🔗 Related Examples

- [E2E Batch Inference](../e2e/) - Traditional ML pipeline patterns
- [LLM Fine-tuning](../llm_finetuning/) - Training custom language models
- [Quickstart](../quickstart/) - Basic ZenML concepts

---

This example demonstrates ZenML's power in bringing MLOps rigor to the rapidly evolving world of AI agents. The same principles that made traditional ML reliable can make your AI systems reliable too.