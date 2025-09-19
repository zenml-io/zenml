# ZenML Quickstart: From Agent-Only to Agent+Classifier

Build a customer support agent that evolves from generic to specialized responses - all without changing code.

## 🎯 What You'll Learn

This quickstart demonstrates the evolution from generic LLM responses to structured, intent-driven customer support. You'll see how adding a simple intent classifier dramatically improves response quality and user experience. We will:

- Deploy a generic LLM agent that gives general banking advice
- Train an intent classifier and tag it as "production"
- Compare generic responses vs. structured, targeted responses
- Evaluate performance with metrics and visualizations

### Understanding ZenML Pipelines

In ZenML, a **pipeline** is a series of connected steps that process data:
- Each **step** is a Python function that performs a specific task
- Steps can pass data (artifacts) between each other
- The same pipeline concept works for both:
  - **Batch mode**: Run once to train models (e.g., `python run.py`)
  - **Deployed mode**: Serve continuously for real-time predictions (e.g., `zenml pipeline deploy`)

This quickstart shows both modes in action:
1. A **serving pipeline** deployed as an API endpoint for customer support
2. A **training pipeline** to create an intent classifier
3. An **evaluation pipeline** to compare response quality

Example of a simple pipeline:

```python
@pipeline
def my_pipeline():
    data = load_data()        # Step 1: Load data
    model = train_model(data) # Step 2: Train model using data from step 1
    do_agentic_loop(model)    # Step 3: Evaluate the model with an agent (toy example)
```

**Key insight**: ZenML unifies batch training and real-time serving with the same primitives.

## 🚀 Quick Start

### Prerequisites
```bash
pip install "zenml[server]" scikit-learn openai
export OPENAI_API_KEY=sk-xxx  # Optional - works without it
```

**Requirements:**
- Docker must be installed and running (used for pipeline deployment)

### Setup
```bash
zenml init
zenml login  # Choose between running locally or with a deployed ZenML server
zenml deployer register docker -f docker
zenml stack register docker-deployer -o default -a default -D docker --set
```

### Phase 1: Deploy Generic LLM Agent

Deploy the agent serving pipeline as a REST API. This creates a running service that gives generic banking advice without intent classification:

```bash
zenml pipeline deploy pipelines.support_agent.support_agent -c configs/agent.yaml
```

Monitor logs:
```bash
zenml deployment logs support_agent -f
```

Test it:
```bash
zenml deployment invoke support_agent \
  --text="my card is lost and i need a replacement"
```

**Result**: Generic response - `"intent": "general", "response": "I understand you need banking assistance. Please contact our support team for personalized help."`

### Phase 2: Train Intent Classifier

```bash
python run.py --train
```

This trains a TF-IDF + LogisticRegression classifier on banking intents and tags it as "production".

### Phase 3: Upgrade to Structured Responses

Update the existing deployment. The agent service will restart and automatically load the newly trained "production" classifier:

```bash
zenml pipeline deploy pipelines.support_agent.support_agent -c configs/agent.yaml -u
```

Test again - **same command, better response**:
```bash
zenml deployment invoke support_agent \
  --text="my card is lost and i need a replacement"
```

**Result**: Targeted response - `"intent": "card_lost", "response": "I'll help you with your lost card immediately. Let me freeze your current card and start the replacement process. You should receive your new card within 3-5 business days."`

### Phase 4: Evaluate Performance

See the dramatic difference! Run evaluation to compare generic vs. structured responses:

```bash
python run.py --evaluate
```

This generates:
- Accuracy & F1 scores comparing generic vs. classified responses
- Response time analysis
- Confusion matrices with ZenML styling
- Performance comparison visualizations

## 🤖 How It Works

The agent checks for production models at startup:

```python
@pipeline(on_init=on_init_hook)  # Runs once at deployment
def support_agent(text: str, use_classifier: bool):
    classification = classify_intent(text, use_classifier)
    response = generate_response(classification)
    return response
```

The magic happens in the init hook:
```python
def on_init_hook():
    # Find artifact tagged "production"
    if production_classifier_exists:
        load_and_use_it()  # Agent upgraded!
```

## 🏗️ Key ZenML Features

- **Unified Workflows**: Same pipeline concept for training (batch), serving (deployed), and evaluation
- **Production Tagging**: `add_tags(tags=["production"])` in training
- **Warm Serving**: Models load once at startup, not per request
- **Auto-upgrade**: Deployments find and use production artifacts
- **Built-in Evaluation**: Compare model performance with rich visualizations

## 📁 Project Structure

```
quickstart/
├── run.py                          # Training & Evaluation CLI
├── utils.py                        # Shared utilities (LLM calls, classifier manager)
├── configs/agent.yaml              # Deployment config
├── pipelines/
│   ├── intent_training_pipeline.py # Batch training (TF-IDF + LogisticRegression)
│   ├── support_agent.py            # Real-time serving with auto-upgrade
│   └── evaluation_pipeline.py      # Performance comparison with visualizations
├── steps/                          # Pipeline steps
│   ├── data.py                     # Banking intent dataset (50+ examples)
│   ├── train.py                    # Training step with production tagging
│   ├── infer.py                    # Inference with generic/structured responses
│   └── evaluate.py                 # Comparison with confusion matrices
└── visualizations/                 # HTML templates and CSS
    ├── __init__.py                 # Template rendering utilities
    ├── evaluation_template.html    # HTML template for performance comparison
    └── styles.css                  # ZenML-styled CSS for dashboard
```

## 🔄 What's Next?

This quickstart shows the foundation. In production, you might:

- **Collect real conversation data** from agent interactions
- **Fine-tune larger models** (DistilBERT, small LLMs) for better accuracy
- **A/B test model versions** by deploying different tagged artifacts
- **Scale to multiple intents** with hierarchical classification
- **Add confidence monitoring** and automated retraining

## 🎯 The Big Picture

This demonstrates ZenML's core value: **one framework for ML and Agents**. Train offline, tag as production, serve online, evaluate performance - all with the same developer experience.

---

**Ready to build your own AI workflows?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams