# Agent Architecture Comparison Pipeline

This example demonstrates how to use ZenML to compare different AI agent architectures in a reproducible, data-driven way. It showcases the unified MLOps approach for both traditional ML models and modern AI agents.

## 🎯 What This Example Demonstrates

- **Multi-Architecture Agent Comparison**: Compare three different customer service agent approaches with interactive visualizations
- **Traditional ML Integration**: Train a scikit-learn intent classifier alongside AI agents
- **LangGraph Workflow**: Implement a real [LangGraph](https://www.langchain.com/langgraph) agent with structured workflow
- **LiteLLM Integration**: Use [LiteLLM](https://litellm.ai/) for unified access to 100+ LLM providers (OpenAI, Anthropic, Groq, etc.)
- **Langfuse Observability**: Track LLM calls, costs, and performance with [Langfuse](https://langfuse.com/) integration
- **Smart LLM Fallbacks**: Automatically use real LLMs when API keys are available, fall back to mock responses otherwise
- **Rich Visualizations**: Automatic generation of interactive Mermaid diagrams through custom materializers
- **Reproducible AI Evaluation**: Apply MLOps principles to agent development

## 🏗️ Architecture Overview

The pipeline implements three agent architectures, each with its own interactive Mermaid diagram:

1. **SingleAgentRAG**: Simple RAG agent handling all queries with one unified approach
   - Knowledge base lookup → LLM/fallback processing → response
   
2. **MultiSpecialistAgents**: Multiple specialized agents with intelligent routing
   - Query routing → specialist selection → domain-specific processing → response
   
3. **LangGraphCustomerServiceAgent**: Structured workflow with observability:
   ```
   START → analyze_query → classify_intent → generate_response → validate_response → END
   ```

All three architectures are automatically visualized with interactive diagrams through custom ZenML materializers, making it easy to understand the differences between approaches.

## 🚀 Quick Start

### Prerequisites

```bash
# Install ZenML with required integrations
pip install "zenml[server]"

# Initialize ZenML
zenml init
```

### Optional: Enable Real LLM Calls & Observability

The pipeline automatically detects API keys and uses real LLMs when available:

```bash
# For OpenAI (recommended)
export OPENAI_API_KEY="your-api-key-here"

# Or use other providers supported by LiteLLM
export ANTHROPIC_API_KEY="your-anthropic-key"
export GROQ_API_KEY="your-groq-key"
export COHERE_API_KEY="your-cohere-key"

# Optional: Enable Langfuse observability (tracks costs, performance, traces)
# Note: LiteLLM requires Langfuse v2, ensure you have: pip install "langfuse>=2,<3"
export LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"
export LANGFUSE_SECRET_KEY="your-langfuse-secret-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"  # or self-hosted

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
# - Interactive Mermaid diagrams for all three architectures
# - Beautiful HTML comparison report
# - Langfuse traces (if enabled) for LLM call observability
```

## 📁 Project Structure

The example has been refactored into a clean modular structure:

```
examples/agent_comparison/
├── agents.py                    # Agent architecture implementations
├── llm_utils.py                # LLM utilities and fallback logic
├── materializers/              # Custom ZenML materializers
│   ├── __init__.py
│   ├── agent_materializer.py   # BaseAgent materializer with visualizations
│   ├── prompt_materializer.py  # Prompt materializer
│   └── prompt.py               # Prompt data model
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
) -> Tuple[Dict, BaseAgent, BaseAgent, BaseAgent]:
    # Tests all three architectures on the same data
    # Returns performance metrics and the three agent instances
    # Visualizations are automatically generated by the AgentMaterializer
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

- **Automatic Agent Visualizations**: Custom ZenML materializers generate interactive diagrams
  - **AgentMaterializer**: Automatically creates Mermaid diagrams and text descriptions for each agent
  - **SingleAgentRAG**: Simple RAG workflow with knowledge base lookup
  - **MultiSpecialistAgents**: Routing-based system with specialized experts
  - **LangGraphCustomerServiceAgent**: Structured multi-step workflow
- **HTML Performance Report**: Styled comparison with metrics, recommendations, and next steps
- **ZenML Dashboard Integration**: All artifacts beautifully rendered with rich visualizations
- **Langfuse Observability**: LLM call traces, cost tracking, and performance monitoring (when enabled)

## 🔧 Customization

### Add Your Own Agent Architecture

```python
class YourCustomAgent(BaseAgent):
    def __init__(self, prompts: Optional[List[Prompt]] = None):
        super().__init__("YourCustomAgent", prompts)
    
    def process_query(self, query: str) -> AgentResponse:
        # Your implementation here
        return AgentResponse(text="...", latency_ms=..., confidence=..., tokens_used=...)
    
    def get_mermaid_diagram(self) -> str:
        """Return HTML with Mermaid diagram for automatic visualization."""
        return """<!DOCTYPE html>..."""
    
    def get_graph_visualization(self) -> str:
        """Return text description for automatic visualization."""
        return "YourCustomAgent Architecture: ..."

# Add to the architectures dictionary in run_architecture_comparison()
# The AgentMaterializer will automatically generate visualizations
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

### LiteLLM + Langfuse Integration

The pipeline automatically uses real LLMs when API keys are detected, with optional Langfuse observability:

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
    max_tokens=200,
    # Langfuse integration (automatic when env vars are set)
    metadata={"agent_type": "SingleAgentRAG", "query_length": len(query)}
)
```

**Supported Providers via LiteLLM:**
- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Groq**: `groq/llama2-70b-4096`, `groq/mixtral-8x7b-32768`
- **Cohere**: `command-r`, `command-r-plus`
- **100+ other providers** - see [LiteLLM docs](https://docs.litellm.ai/docs/providers)

**Langfuse Observability Benefits:**
- **Cost Tracking**: Monitor LLM costs across different providers and models
- **Performance Monitoring**: Track latency, throughput, and error rates
- **Trace Analysis**: See complete request/response flows for debugging
- **Model Comparison**: Compare performance metrics across different LLMs

## 📚 Key Concepts Demonstrated

- **Unified MLOps**: Same framework for traditional ML and AI agents
- **Custom Materializers**: Automatic visualization generation for complex artifacts
- **Reproducible AI**: Version control for prompts, models, and agent configurations  
- **Data-Driven Decisions**: Systematic evaluation rather than subjective choices
- **Pipeline Orchestration**: Structured workflows with proper dependencies
- **Artifact Tracking**: All inputs, outputs, and metadata automatically logged
- **Automatic Visualization**: Rich HTML and interactive diagrams generated by materializers

## 🌐 LLM Ecosystem Integration

This example demonstrates ZenML's seamless integration with the modern AI landscape:

### 🔗 **LangGraph** - Structured Agent Workflows
- Build complex, multi-step agent workflows with full observability
- Each workflow step is tracked and versioned by ZenML
- Interactive Mermaid diagrams show your agent's decision flow
- Complete lineage tracking from inputs to final responses

### ⚡ **LiteLLM** - Universal LLM Access  
- Single interface to 100+ LLM providers (OpenAI, Anthropic, Groq, Cohere, etc.)
- Automatic fallbacks and smart provider switching
- Unified API regardless of provider-specific differences
- Cost optimization through provider comparison

### 📊 **Langfuse** - LLM Observability & Analytics
- Complete trace visibility for every LLM call across all architectures
- Real-time cost tracking and budget monitoring
- Performance analytics: latency, tokens, success rates
- Debug complex agent workflows with detailed execution traces
- Compare model performance across different providers

### 🤝 Integration Points

This example shows how to integrate:
- **LangGraph**: For structured agent workflows with full lineage tracking
- **LiteLLM**: For unified access to the entire LLM ecosystem
- **Langfuse**: For comprehensive LLM observability and cost tracking
- **scikit-learn**: For traditional ML components alongside AI agents
- **ZenML**: For orchestration, versioning, and artifact tracking
- **HTML/Mermaid**: For rich visualizations and interactive diagrams

**The Result**: A unified MLOps approach that works for everything from decision trees to complex agent workflows, with full observability across the entire AI stack.

## 🎯 Production Readiness

To make this production-ready:

1. **Add Real Data Sources**: Replace sample data with your actual customer queries
2. **Implement Real LLMs**: Connect to OpenAI, Anthropic, or other LLM providers
3. **Enable Full Observability**: Set up Langfuse for cost tracking and performance monitoring
4. **Add More Metrics**: Include customer satisfaction scores, resolution rates, etc.
5. **Scale Testing**: Run on larger datasets and more architectures
6. **Add Monitoring**: Track performance degradation over time with Langfuse dashboards
7. **Implement A/B Testing**: Gradually roll out winning architectures with proper monitoring

## 🔗 Related Examples

- [E2E Batch Inference](../e2e/) - Traditional ML pipeline patterns
- [LLM Fine-tuning](../llm_finetuning/) - Training custom language models
- [Quickstart](../quickstart/) - Basic ZenML concepts

---

This example demonstrates ZenML's power in bringing MLOps rigor to the rapidly evolving world of AI agents. The same principles that made traditional ML reliable can make your AI systems reliable too.