# Agent Outer Loop: Transform Generic AI to Specialized Support Agent

See how ZenML enables you to evolve a generic banking agent into a specialized support system that gives targeted responses.

## 🎯 What You'll Learn

This example demonstrates the agent outer loop pattern: starting with a generic agent, training an intent classifier, and automatically upgrading the agent to use the classifier. You'll see how ZenML makes this evolution seamless:

- Deploy a generic banking advice agent that gives general banking advice
- Train an intent classifier and tag it as "production"
- Upgrade the deployed agent automatically (it detects the new classifier)
- Compare generic responses vs. specialized, targeted responses
- Evaluate performance with metrics and visualizations

### Understanding ZenML Pipelines

In ZenML, a **pipeline** is a series of connected steps that process data:
- Each **step** is a Python function that performs a specific task
- Steps can pass data (artifacts) between each other
- The same pipeline concept works for both:
  - **Batch mode**: Run once to train models (e.g., `python run.py`)
  - **Deployed mode**: Serve continuously for real-time predictions (e.g., `zenml pipeline deploy`)

Example of a simple pipeline:

```python
@pipeline
def my_pipeline():
    data = load_data()        # Step 1: Load data
    model = train_model(data) # Step 2: Train model using data from step 1
    do_agentic_loop(model)    # Step 3: Use model with an agent (toy example)
```

**Key insight**: ZenML unifies batch training and real-time serving with the same primitives.

This quickstart shows both modes in action:
1. A **serving pipeline** deployed as an API endpoint for customer support
2. A **training pipeline** to create an intent classifier
3. An **evaluation pipeline** to compare response quality

Note, this is purely a toy example meant to illustrate some of the key concepts of ZenML. It is not meant as a production-grade template for this use-case.

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-xxx  # Optional - works without it
```

### Setup
```bash
zenml init
zenml login  # Choose between running locally or with a deployed ZenML server
```

### Phase 1: Run The Agent in Batch Mode

First, let's run the agent pipeline directly in batch mode to see how it works without deployment. This runs the pipeline once and returns the result:

```bash
python run.py --agent --text "I want to open a savings account"
```

The agent runs without a classifier (none has been trained yet), so it falls back to generic LLM responses.

**Key insight**: In batch mode, you need to run the pipeline each time you want a response. This is fine for testing but not practical for a customer support system.

### Phase 2: Deploy Generic Banking Advice Agent

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

### Phase 3: Train Intent Classifier

```bash
python run.py --train    # Train classifier and tag as production
```

This trains a TF-IDF + LogisticRegression classifier on 8 banking intent categories (70+ examples) and automatically tags the best model as "production" for the serving pipeline to discover.

### Phase 4: Upgrade to Structured Responses

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

### Phase 5: Evaluate Performance

See the dramatic difference! Run evaluation to compare generic vs. structured responses:

```bash
python run.py --evaluate   # Compare agent performance
```

This generates rich visualizations viewable in the ZenML dashboard:
- Accuracy & F1 scores comparing generic vs. classified responses
- Response time analysis
- Confusion matrices with ZenML styling
- Performance comparison charts
- Interactive HTML reports with detailed metrics

**View Results**: After running evaluation, visit your ZenML dashboard to see the generated visualizations and detailed performance comparison.

Note: The cloud training configs at `configs/training_{aws,azure,gcp}.yaml` are maintained for our CI/release validation and aren't required for this quickstart. For local runs, just use `python run.py` (with `--train`/`--evaluate`) as shown above—no cloud config needed.

## 🤖 How It Works

The agent checks for production models at startup:

```python
@pipeline(on_init=on_init_hook)  # Runs once at deployment
def support_agent(text: str, use_classifier: bool):
    classification = classify_intent(text, use_classifier)
    response = generate_response(classification)
    return response
```

The magic happens in the init hook (learn more about [ZenML hooks](https://docs.zenml.io/how-to/pipeline-development/use-pipeline-step-hooks)):
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

- **Collect real conversation data** from agent interactions via tracing tools like Langfuse, Datadog, etc.
- **Fine-tune larger models** (DistilBERT, small LLMs) for better accuracy
- **A/B test model versions** by deploying different tagged artifacts
- **Deploy to any cloud infrastructure** with [stacks](https://docs.zenml.io/stacks)

## 🎯 The Big Picture

This demonstrates ZenML's core value: **one framework for ML and Agents**. Train offline, tag as production, serve online, evaluate performance - all with the same developer experience.

---

**Ready to build your own AI workflows?**

- 📖 [Full ZenML Documentation](https://docs.zenml.io/)
- 💬 [Join our Community](https://zenml.io/slack)
- 🏢 [ZenML Pro](https://zenml.io/pro) for teams
