# ZenML Quickstart: From Agent-Only to Agent+Classifier

**The modern AI development story in 5 minutes.**

This quickstart demonstrates how ZenML unifies ML and Agent workflows, showing the natural progression from a generic agent to a specialized one powered by your own trained models.

## 🎯 The Story

**Phase 1**: Deploy a support agent → Generic responses
**Phase 2**: Train an intent classifier → Tag as "production"
**Phase 3**: Same agent automatically upgrades → Specialized responses

**The "aha" moment**: ZenML connects batch training and real-time serving with the same primitives. Train offline, promote artifacts to production, and agents automatically consume them online.

## 🚀 Quick Start

### Prerequisites
```bash
pip install "zenml[server]" scikit-learn
```

### Setup
```bash
# Initialize ZenML repository
zenml init

# Set up deployer stack (required for serving)
zenml deployer register docker -f docker
zenml stack register docker-deployer -o default -a default -D docker --set
```

### Phase 1: Deploy Agent-Only

Deploy the agent without any classifier - it will use generic responses:

```bash
zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline \
  -n support-agent -c configs/agent.yaml
```

Test it:
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "confidence_threshold": 0.65,
      "text": "my card is lost and i need a replacement"
    }
  }'
```

Or use the ZenML CLI:
```bash
zenml deployment invoke support-agent \
  --confidence_threshold=0.65 \
  --text="my card is lost and i need a replacement"
```

**Response**: Generic banking response with `"intent_source": "llm"`
```json
{
  "answer": "I'm here to help with your banking needs. I can assist with card issues, payments, account balances, disputes, and credit limit requests. What specific question can I help you with today?",
  "intent": "general",
  "confidence": 0.0,
  "intent_source": "llm"
}
```

### Phase 2: Train Classifier

Train an intent classifier and automatically tag it as "production":

```bash
python run.py --train
```

**Example output**:
```
>> Running intent_training_pipeline (auto-tags artifact VERSION as 'production').
Loaded 20 training examples across 6 intents:
  - account_balance: 3 examples
  - card_lost: 4 examples
  - credit_limit: 2 examples
  - dispute: 3 examples
  - general: 4 examples
  - payments: 4 examples
Training classifier on 20 examples...
Training completed!
Accuracy on test set: 0.333
Tagged artifact version as 'production'
>> Done. Check dashboard: artifact 'intent-classifier' latest version has tag 'production'.
```

**What happens**:
- Loads toy banking support dataset (20 examples, 6 intents)
- Trains TF-IDF + LogisticRegression classifier
- **Automatically tags the artifact version as "production"**
- Shows training metrics and accuracy

### Phase 3: Agent Automatically Upgrades

Update the same deployment (the agent will now load the production classifier):

```bash
zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline \
  -n support-agent -c configs/agent.yaml -u
```

Test with the same request (using lower threshold to see classifier in action):
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "confidence_threshold": 0.3,
      "text": "my card is lost and i need a replacement"
    }
  }'
```

Or with ZenML CLI:
```bash
zenml deployment invoke support-agent \
  --confidence_threshold=0.3 \
  --text="my card is lost and i need a replacement"
```

**Response**: Specific card replacement instructions with `"intent_source": "classifier"`
```json
{
  "answer": "I understand you've lost your card. Here are the immediate steps: 1) Log into your account to freeze the card, 2) Call our 24/7 hotline at 1-800-SUPPORT, 3) Order a replacement card through the app. Your new card will arrive in 3-5 business days.",
  "intent": "card_lost",
  "confidence": 0.41,
  "intent_source": "classifier"
}
```

**Notice the difference**:
- **Phase 1**: Generic response, `"intent_source": "llm"`
- **Phase 3**: Specific response, `"intent_source": "classifier"`, actual intent detected

## 🔍 What's Happening Under the Hood

### Training Pipeline (`intent_training_pipeline`)
```python
@pipeline
def intent_training_pipeline():
    texts, labels = load_toy_intent_data()           # Load training data
    classifier = train_classifier_step(texts, labels) # Train + tag as "production"
    return classifier
```

### Agent Serving Pipeline (`agent_serving_pipeline`)
```python
@pipeline(on_init=on_init_hook)  # 🔥 Key feature: warm start
def agent_serving_pipeline(text: str, confidence_threshold: float = 0.65):
    classification = classify_intent(text, confidence_threshold)
    response = generate_response(classification)
    return response
```

### The Magic: Production Artifact Loading
```python
def on_init_hook():
    """Load production classifier if available - runs once at deployment startup"""
    client = Client()
    versions = client.list_artifact_versions(name="intent-classifier")

    # Find version tagged "production"
    for version in versions:
        if version.tags and "production" in [tag.name for tag in version.tags]:
            global _router
            _router = version.load()  # 🎯 Warm-loaded and ready!
            break
```

## 📊 Intent Classification

The demo includes 6 banking support intents:

- **`card_lost`**: "my card is lost and i need a replacement"
- **`payments`**: "i need to make a payment"
- **`account_balance`**: "what is my current balance"
- **`dispute`**: "i want to dispute a charge"
- **`credit_limit`**: "can you increase my credit limit"
- **`general`**: "hello", "can you help me"

Each intent triggers a specific, helpful response with clear next steps.

## 🎭 Confidence-Based Routing

The agent uses confidence thresholds to decide when to trust the classifier:

```python
if classifier_confidence >= threshold:
    # Use specific intent (e.g., "card_lost")
    intent_source = "classifier"
else:
    # Fall back to general response
    intent_source = "classifier_fallback"
```

**Demo tip**: Use `confidence_threshold: 0.3` to see classifier predictions, `0.65` for fallback behavior.

## 🏗️ ZenML Features Demonstrated

### 🔄 **Unified ML + Agent Workflows**
- Same pipeline primitives for batch training and real-time serving
- Seamless artifact flow from training → production → serving

### 🏷️ **Production Artifact Tagging**
```python
# In training step
add_tags(tags=["production"], infer_artifact=True)
```

### ⚡ **Warm Container Serving**
- Models load once at startup (`on_init` hook)
- Sub-second response times for real requests
- Stateful serving with persistent connections

### 📈 **Artifact Lineage**
- Track data → model → deployment relationships
- Version comparison and rollback capabilities
- Full audit trail of what's running where

### 🔧 **Stack Portability**
```bash
# Same code, different infrastructure
zenml stack set aws-stack
zenml pipeline deploy ... # Now running on AWS!
```

## 🌟 Key Takeaways

1. **Start Simple**: Deploy agents quickly without complex ML infrastructure
2. **Evolve Naturally**: Add specialized models when you have data and business need
3. **Unified Framework**: Use the same ZenML primitives for everything
4. **Production Ready**: Automatic versioning, lineage, and deployment management

## 🔄 What's Next?

This quickstart shows the foundation. In production, you might:

- **Collect real conversation data** from agent interactions
- **Fine-tune larger models** (DistilBERT, small LLMs) for better accuracy
- **A/B test model versions** by deploying different tagged artifacts
- **Scale to multiple intents** with hierarchical classification
- **Add confidence monitoring** and automated retraining

## 📁 Project Structure

```
examples/quickstart/
├── README.md                           # This file
├── requirements.txt                    # Dependencies
├── run.py                             # Training CLI
├── configs/agent.yaml                 # Deployment configuration
├── pipelines/
│   ├── intent_training_pipeline.py    # Batch training workflow
│   └── agent_serving_pipeline.py      # Real-time agent serving
└── steps/
    ├── data.py                        # Intent dataset
    ├── train.py                       # Classifier training + tagging
    └── infer.py                       # Intent classification + response
```

## 🎯 The Big Picture

**This quickstart demonstrates ZenML's core value proposition**:

*One framework for ML and Agents. Train offline, promote artifacts into production, and serve online with the same developer experience.*

Whether you're building classical ML pipelines or modern agentic workflows, ZenML provides the infrastructure to make them reliable, reproducible, and production-ready.

---

**Ready to build your own AI workflows?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams