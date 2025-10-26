# ZenML Quickstart

Get started with ZenML in minutes. This quickstart demonstrates the core ZenML concepts: pipelines, steps, and artifacts.

## 🎯 What You'll Learn

- Create a simple ZenML pipeline
- Run it locally for development
- Deploy it as a managed HTTP endpoint
- Track artifacts and metadata automatically

## 🚀 Quick Start

### Prerequisites

```bash
pip install "zenml[server]"
zenml init
```

### Phase 1: Run Locally

Run the pipeline locally to see ZenML in action:

```bash
pip install -r requirements.txt
python run.py
```

This executes a simple pipeline and tracks all artifacts in your local ZenML instance.

### Phase 2: View in Dashboard

See your pipeline runs, artifacts, and metadata:

```bash
zenml login  # If you haven't already
```

Open your browser to the ZenML dashboard (URL shown after login) to visualize your pipeline run.

### Phase 3: Create a Pipeline Snapshot (Optional)

Create an immutable snapshot of your pipeline for reproducibility and sharing:

```bash
zenml pipeline snapshot create pipelines.simple_pipeline.simple_pipeline --name my_snapshot
```

Snapshots freeze your pipeline code, configuration, and container images so:
- **Reproducibility**: Run the exact same pipeline months later
- **Collaboration**: Share ready-to-use pipeline configs with teammates
- **Automation**: Trigger from dashboards or CI/CD systems without code access

### Phase 4: Deploy as an HTTP Service

As well as running a pipeline in batch mode, ZenML allows you to deploy the same pipeline as a real-time HTTP service:

```bash
# Deploy your pipeline directly
zenml pipeline deploy pipelines.simple_pipeline.simple_pipeline

# OR deploy a snapshot (if you created one above)
zenml pipeline snapshot deploy my_snapshot --deployment simple_pipeline
```

**Key insight**: `zenml pipeline deploy` automatically creates an implicit snapshot behind the scenes!

Get your deployment URL:

```bash
zenml deployment describe simple_pipeline
```

### Phase 5: Invoke Your Deployed Service

Call your deployed pipeline as an HTTP endpoint:

```bash
# Using ZenML CLI
zenml deployment invoke simple_pipeline --name="Alice"

# Using curl
ENDPOINT=http://localhost:8000  # Replace with your deployment URL
curl -X POST "$ENDPOINT/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"name": "Bob"}}'
```

**Key insight**: Your pipeline now runs as a persistent HTTP service. Same code, real-time inference!

### Phase 6: Run on Cloud (Optional)

Run the same pipeline on cloud infrastructure without changing any code:

```bash
# Create a cloud stack
zenml stack create my_cloud_stack --orchestrator kubeflow --artifact-store s3 --deployer aws...

# Activate it
zenml stack set my_cloud_stack

# Run the same code - it automatically runs on the cloud!
python run.py

# Or deploy the pipeline directly on your cloud infrastructure!
zenml pipeline deploy pipelines.simple_pipeline.simple_pipeline
```

**Key insight**: ZenML separates ML code from infrastructure. Your pipeline runs identically locally, deployed as a service, or in the cloud!

## 📦 Project Structure

```
quickstart/
├── run.py                      # Main entry point
├── pipelines/
│   └── simple_pipeline.py      # Pipeline definition
├── steps/
│   └── simple_step.py          # Step definitions
├── requirements.txt            # Dependencies
└── configs/
    └── default.yaml            # Pipeline configuration
```

## 📚 Next Steps

- **LLM Agent Example**: Check out `examples/deploying_agent/` for document analysis with an embedded web UI
- **Agent Training Loop**: See `examples/agent_outer_loop/` for a comprehensive agent with training and evaluation
- **Classical ML**: Explore `examples/deploying_ml_model/` for traditional ML workflows
- **Documentation**: Read the [ZenML docs](https://docs.zenml.io/)
