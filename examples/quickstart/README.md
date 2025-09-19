# ZenML Quickstart: From Agent-Only to Agent+Classifier

**The modern AI development story in 5 minutes.**

## 🎯 What You'll Learn

This quickstart demonstrates how ZenML unifies ML and Agent workflows, showing the natural progression from a generic agent to a specialized one powered by your own trained models. We will:

- Deploy an agent as a REST API using ZenML pipelines
- Train a classifier and tag it as "production"
- Watch the agent automatically upgrade itself with the new model

### Understanding ZenML Pipelines

In ZenML, a **pipeline** is a series of connected steps that process data:
- Each **step** is a Python function that performs a specific task
- Steps can pass data (artifacts) between each other
- The same pipeline concept works for both:
  - **Batch mode**: Run once to train models (e.g., `python run.py`)
  - **Deployed mode**: Serve continuously for real-time predictions (e.g., `zenml pipeline deploy`)

This quickstart shows both modes in action:
1. A **serving pipeline** deployed as an API endpoint for the agent
2. A **training pipeline** run in batch to create a classifier

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

### Setup
```bash
zenml init
zenml login  # Choose between running this locally, or with a deployed ZenML server
zenml deployer register docker -f docker
zenml stack register docker-deployer -o default -a default -D docker --set
```

### Phase 1: Deploy Agent

Deploy the agent serving pipeline as a REST API. This creates a running service that can handle customer queries. Without a trained classifier, it will use generic responses:

```bash
zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline \
  -n support-agent -c configs/agent.yaml
```

Test it:
```bash
zenml deployment invoke support-agent \
  --text="my card is lost and i need a replacement"
```

**Result**: Generic response - `"intent": "general", "intent_source": "llm"`

### Phase 2: Train Classifier

```bash
python run.py --train
```

This trains a classifier on banking intents and tags it as "production".

### Phase 3: Agent Auto-Upgrades

Update the existing deployment. The agent service will restart and automatically load the newly trained "production" classifier:

```bash
zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline \
  -n support-agent -c configs/agent.yaml -u
```

Test again - **same command, better response**:
```bash
zenml deployment invoke support-agent \
  --text="my card is lost and i need a replacement"
```

**Result**: Specific response - `"intent": "card_lost", "intent_source": "classifier"`

## 🤖 How It Works

The agent checks for production models at startup:

```python
@pipeline(on_init=on_init_hook)  # Runs once at deployment
def agent_serving_pipeline(text: str):
    classification = classify_intent(text)
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

- **Unified Workflows**: Same pipeline concept for training (batch) and serving (deployed)
- **Production Tagging**: `add_tags(tags=["production"])` in training
- **Warm Serving**: Models load once at startup, not per request
- **Auto-upgrade**: Deployments find and use production artifacts

## 📁 Project Structure

```
quickstart/
├── run.py                          # Training CLI
├── configs/agent.yaml              # Deployment config
├── pipelines/
│   ├── intent_training_pipeline.py # Batch training
│   └── agent_serving_pipeline.py   # Real-time serving
└── steps/                          # Pipeline steps
```

## 🎯 The Big Picture

This demonstrates ZenML's core value: **one framework for ML and Agents**. Train offline, tag as production, serve online - all with the same developer experience.

---

**Next Steps:**
- 📖 [Docs](https://docs.zenml.io/) | 💬 [Community](https://zenml.io/slack) | 🏢 [ZenML Pro](https://zenml.io/pro)