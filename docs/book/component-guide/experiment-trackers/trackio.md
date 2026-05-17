---
description: Logging and visualizing experiments with Trackio.
---

# Trackio Integration with ZenML

## Overview

The Trackio integration for ZenML enables experiment tracking, metric logging, artifact management, and Hugging Face ecosystem publishing directly inside ZenML pipelines.

The integration connects ZenML's pipeline orchestration layer with Trackio's lightweight experiment tracking runtime, allowing users to monitor and publish machine learning workflows with minimal operational overhead.

### Supported Features

- Local experiment tracking
- Hugging Face Space dashboards
- Dataset publishing
- Artifact logging
- Metric visualization
- System and GPU telemetry
- Static dashboard workflows
- Full Hugging Face ecosystem integration

The tracker is implemented as a ZenML experiment tracker flavor and lifecycle integration.

---

## How the Integration Works

During pipeline execution, the integration follows this workflow:

1. ZenML initializes the active experiment tracker
2. The Trackio integration creates a Trackio run
3. ZenML pipeline metadata is injected automatically
4. Metrics, artifacts, and metadata are logged to Trackio
5. Optional synchronization and publishing actions are executed
6. Run metadata and dashboard URLs are attached back to the ZenML run

Internally, the integration hooks into the ZenML step lifecycle using:

- `prepare_step_run`
- `cleanup_step_run`
- `get_step_run_metadata`

---

## Backend Support

The integration supports multiple Trackio backend modes through the backend configuration field.

| Backend | Description |
|---------|-------------|
| sqlite | Local lightweight tracking |
| space | Hugging Face Space-hosted dashboards |
| http | Remote Trackio server |
| static | Static deployment mode |

This allows the same ZenML pipeline to run locally or publish hosted dashboards without changing pipeline logic.

---

## Configuration

The integration exposes two configuration layers:

### Tracker Configuration

`TrackioExperimentTrackerConfig` defines backend and deployment behavior.

Important fields include:

| Field | Description |
|-------|-------------|
| project_name | Trackio project name |
| backend | Backend type |
| tracking_uri | Optional backend URI |
| local_dir | Local tracking directory |
| hf_token | Hugging Face authentication token |
| hf_space | Hugging Face Space dashboard |
| hf_dataset_repo | Dataset repository |
| publish_to_space | Publish dashboards automatically |
| publish_to_dataset | Publish logs automatically |

### Runtime Settings

`TrackioExperimentTrackerSettings` controls runtime behavior.

Supported settings include:

| Setting | Description |
|---------|-------------|
| run_name | Custom run name |
| tags | Run tags |
| resume | Resume policy |
| auto_sync | Automatically sync runs |
| auto_freeze | Freeze dashboards |
| log_system_metrics | System telemetry |
| log_gpu_metrics | GPU telemetry |

---

## Complete Integration Example

### Overview

The example pipeline demonstrates a complete Hugging Face + ZenML + Trackio workflow. The pipeline performs:

- Dataset loading from Hugging Face Datasets
- Sentiment inference using Transformers
- Metric logging with Trackio
- Artifact saving
- Dataset publishing to Hugging Face Hub
- Dashboard synchronization

### Active Experiment Tracker

The currently active experiment tracker is resolved from the ZenML stack:

```python
experiment_tracker = (
    Client()
    .active_stack
    .experiment_tracker
)
```

This allows the pipeline to remain environment-independent while inheriting the configured experiment tracker automatically.

### Hugging Face Integration Targets

```python
# Input dataset consumed by pipeline
HF_INPUT_DATASET = (
    "dair-ai/emotion"
)

# Output dataset containing
# Trackio inference logs/results
HF_OUTPUT_DATASET_REPO = (
    "AINovice2005/"
    "trackio-sentiment-results-v2"
)

# Trackio dashboard Space
HF_SPACE_ID = (
    "AINovice2005/"
    "trackio-sentiment-dashboard-v2"
)

HF_SPACE_URL = (
    "https://huggingface.co/spaces/"
    f"{HF_SPACE_ID}"
)
```

### Dataset Loading

The pipeline loads an input dataset directly from the Hugging Face Hub:

```python
@step
def load_input_dataset() -> Dataset:
    """Load dataset from Hugging Face Hub."""

    dataset = load_dataset(
        HF_INPUT_DATASET,
        split="train[:350]",
    )

    print(
        "\nLoaded input dataset:"
    )

    print(HF_INPUT_DATASET)

    return dataset
```

This step becomes reproducible and version-aware through ZenML.

### Transformers Inference

The example initializes a Hugging Face Transformers sentiment pipeline:

```python
classifier = hf_pipeline(
    task="sentiment-analysis",
    model=(
        "distilbert-base-uncased-"
        "finetuned-sst-2-english"
    ),
)
```

Inference is executed inside the `classify_sentiment` step. Each dataset row is processed individually and converted into structured prediction records.

### Trackio Logging

The integration logs metrics directly through Trackio:

```python
trackio.log(metrics)
```

The example logs:

- Number of samples
- Positive predictions
- Negative predictions
- Confidence scores
- Prediction ratios
- Min/max confidence

Additional metadata is also logged:

```python
trackio.log(
    {
        "model": (
            "distilbert-base-"
            "uncased-finetuned-"
            "sst-2-english"
        ),
        "hf_input_dataset": (
            HF_INPUT_DATASET
        ),
        "sample_predictions": (
            results[:10]
        ),
    }
)
```

### Artifact Management

The pipeline stores prediction outputs and metrics locally before uploading them through Trackio.

Artifacts are written as JSON files and uploaded using:

```python
predictions_path = (
    ARTIFACT_DIR
    / "predictions.json"
)

with open(
    predictions_path,
    "w",
) as f:
    json.dump(
        results,
        f,
        indent=2,
    )

trackio.save(
    str(predictions_path)
)
```

This enables artifact persistence alongside experiment metadata.

### Hugging Face Dataset Publishing

The processed dataset is published back to the Hugging Face Hub:

```python
result_dataset.push_to_hub(
    HF_OUTPUT_DATASET_REPO,
    private=False,
)
```

This creates a reproducible dataset output workflow integrated directly into the pipeline.

### Hugging Face Space Dashboard

The pipeline also publishes dashboard metadata for a Hugging Face Space:

```python
trackio.log(
    {
        "space_status": (
            "published"
        ),
        "space_url": (
            HF_SPACE_URL
        ),
    }
)
```

### Synchronization

The example explicitly synchronizes the Trackio project after execution:

```python
trackio.sync(
    project=experiment_tracker.config.project_name
)
```

This pushes tracked metadata and artifacts into the configured backend.

### Runtime Initialization

Internally, the integration initializes Trackio with ZenML metadata:

```python
config = {
    "zenml": {
        "pipeline_name": (
            info.pipeline.name
        ),
        "step_name": (
            info.pipeline_step_name
        ),
        "run_name": info.run_name,
    }
}
```

The integration dynamically filters unsupported SDK arguments before calling:

```python
trackio.init(**filtered_kwargs)
```

This improves compatibility across Trackio versions and backend modes.

### Automatic Cleanup

At the end of each step, the integration finalizes the Trackio session using:

```python
trackio.finish()
```

Optional synchronization and dashboard freezing can also be enabled through runtime settings.

---

## Full Example Code

```python
"""ZenML + Trackio + Hugging Face ecosystem example."""

from pathlib import Path
import json

import trackio

from datasets import (
    Dataset,
    load_dataset,
)
from transformers import pipeline as hf_pipeline

from zenml import pipeline, step
from zenml.client import Client

from zenml.integrations.trackio.flavors.trackio_experiment_tracker_flavor import (
    TrackioExperimentTrackerSettings,
)

# ---------------------------------------------------------
# Active experiment tracker
# ---------------------------------------------------------

experiment_tracker = (
    Client()
    .active_stack
    .experiment_tracker
)

# ---------------------------------------------------------
# Artifact directory
# ---------------------------------------------------------

ARTIFACT_DIR = Path(
    "./trackio_artifacts"
)

ARTIFACT_DIR.mkdir(
    exist_ok=True
)

# ---------------------------------------------------------
# Hugging Face integration targets
# ---------------------------------------------------------

# Input dataset consumed by pipeline
HF_INPUT_DATASET = (
    "dair-ai/emotion"
)

# Output dataset containing
# Trackio inference logs/results
HF_OUTPUT_DATASET_REPO = (
    "AINovice2005/"
    "trackio-sentiment-results-v2"
)

# Trackio dashboard Space
HF_SPACE_ID = (
    "AINovice2005/"
    "trackio-sentiment-dashboard-v2"
)

HF_SPACE_URL = (
    "https://huggingface.co/spaces/"
    f"{HF_SPACE_ID}"
)

# ---------------------------------------------------------
# Trackio settings
# ---------------------------------------------------------

trackio_settings = (
    TrackioExperimentTrackerSettings(
        auto_sync=False,
        auto_freeze=False,
        resume="allow",
    )
)

# ---------------------------------------------------------
# Hugging Face sentiment pipeline
# ---------------------------------------------------------

classifier = hf_pipeline(
    task="sentiment-analysis",
    model=(
        "distilbert-base-uncased-"
        "finetuned-sst-2-english"
    ),
)

# ---------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------


@step
def load_input_dataset() -> Dataset:
    """Load dataset from Hugging Face Hub."""

    dataset = load_dataset(
        HF_INPUT_DATASET,
        split="train[:350]",
    )

    print(
        "\nLoaded input dataset:"
    )

    print(HF_INPUT_DATASET)

    return dataset


# ---------------------------------------------------------
# Sentiment inference
# ---------------------------------------------------------


@step(
    experiment_tracker=experiment_tracker.name,
    settings={
        "experiment_tracker": (
            trackio_settings
        ),
    },
)
def classify_sentiment(
    dataset: Dataset,
) -> Dataset:
    """Run sentiment inference."""

    results = []

    for row in dataset:
        prediction = classifier(
            row["text"]
        )[0]

        results.append(
            {
                "text": row["text"],
                "ground_truth": (
                    row["label"]
                ),
                "sentiment": (
                    prediction["label"]
                ),
                "score": float(
                    prediction["score"]
                ),
            }
        )

    result_dataset = (
        Dataset.from_list(
            results
        )
    )

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    positive_count = sum(
        1
        for row in results
        if row["sentiment"]
        == "POSITIVE"
    )

    negative_count = sum(
        1
        for row in results
        if row["sentiment"]
        == "NEGATIVE"
    )

    scores = [
        row["score"]
        for row in results
    ]

    metrics = {
        "num_samples": len(
            results
        ),
        "positive_count": (
            positive_count
        ),
        "negative_count": (
            negative_count
        ),
        "positive_ratio": (
            positive_count
            / len(results)
        ),
        "negative_ratio": (
            negative_count
            / len(results)
        ),
        "average_confidence": (
            sum(scores)
            / len(scores)
        ),
        "min_confidence": min(
            scores
        ),
        "max_confidence": max(
            scores
        ),
    }

    # -----------------------------------------------------
    # Trackio logging
    # -----------------------------------------------------

    trackio.log(metrics)

    trackio.log(
        {
            "model": (
                "distilbert-base-"
                "uncased-finetuned-"
                "sst-2-english"
            ),
            "hf_input_dataset": (
                HF_INPUT_DATASET
            ),
            "sample_predictions": (
                results[:10]
            ),
        }
    )

    # -----------------------------------------------------
    # Save local artifacts
    # -----------------------------------------------------

    predictions_path = (
        ARTIFACT_DIR
        / "predictions.json"
    )

    with open(
        predictions_path,
        "w",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    trackio.save(
        str(predictions_path)
    )

    metrics_path = (
        ARTIFACT_DIR
        / "metrics.json"
    )

    with open(
        metrics_path,
        "w",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
        )

    trackio.save(
        str(metrics_path)
    )

    # -----------------------------------------------------
    # Publish output dataset
    # -----------------------------------------------------

    result_dataset.push_to_hub(
        HF_OUTPUT_DATASET_REPO,
        private=False,
    )

    print(
        "\nOutput dataset pushed:"
    )

    print(
        HF_OUTPUT_DATASET_REPO
    )

    # -----------------------------------------------------
    # Publish Space metadata
    # -----------------------------------------------------

    trackio.log(
        {
            "space_status": (
                "published"
            ),
            "space_url": (
                HF_SPACE_URL
            ),
        }
    )

    trackio.sync(project=experiment_tracker.config.project_name)
    print(
        "\nHF Space dashboard:"
    )

    print(HF_SPACE_URL)

    return result_dataset


# ---------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------


@pipeline(
    enable_cache=False,
    enable_pipeline_logs=False,
)
def sentiment_analysis_pipeline():
    """HF + Trackio pipeline."""

    dataset = load_input_dataset()

    classify_sentiment(dataset)


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    print(
        "\nRunning ZenML + "
        "Trackio + HF pipeline...\n"
    )

    pipeline_settings = {
        "experiment_tracker": (
            TrackioExperimentTrackerSettings(
                auto_sync=True,
                auto_freeze=False,
                resume="allow",
            )
        )
    }

    sentiment_analysis_pipeline.with_options(
        settings=pipeline_settings,
    )()

    print(
        "\nPipeline completed successfully."
    )
```

---

## Summary

The Trackio integration extends ZenML with a lightweight experiment tracking layer that supports:

- Metric logging
- Artifact tracking
- Hugging Face publishing
- Hosted dashboards
- Dataset synchronization
- Experiment metadata management

The example pipeline demonstrates how ZenML orchestration, Hugging Face tooling, and Trackio tracking can be combined into a single reproducible ML workflow with minimal infrastructure requirements.

### Key Integration Benefits

- **Hugging Face Ecosystem**: Native integration with Datasets, Models, and Spaces.
- **Multiple Backends**: Supports local SQLite, Hugging Face Spaces, HTTP servers, and static deployments.
- **Automatic Metadata Injection**: Pipeline context (names, run IDs, step names) automatically included.
- **Artifact Management**: Seamless artifact persistence and publishing.
- **Dashboard Publishing**: Export runs to hosted Hugging Face Spaces dashboards.

---

## Troubleshooting

### OpenTelemetry Threading Issue

If you encounter `RuntimeError: can't create new thread at interpreter shutdown`, ensure proper cleanup of OpenTelemetry background threads, this ensures all background threads are shut down cleanly before the interpreter exits.:

```python
def cleanup_otel():
    """Properly flush and shutdown OpenTelemetry SDK."""
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk.metrics import MeterProvider
        
        tracer_provider = TracerProvider()
        logger_provider = LoggerProvider()
        meter_provider = MeterProvider()
        
        if hasattr(tracer_provider, "force_flush"):
            tracer_provider.force_flush(timeout_millis=5000)
        if hasattr(tracer_provider, "shutdown"):
            tracer_provider.shutdown()
            
        if hasattr(logger_provider, "force_flush"):
            logger_provider.force_flush(timeout_millis=5000)
        if hasattr(logger_provider, "shutdown"):
            logger_provider.shutdown()
            
        if hasattr(meter_provider, "force_flush"):
            meter_provider.force_flush(timeout_millis=5000)
        if hasattr(meter_provider, "shutdown"):
            meter_provider.shutdown()
        
    except Exception as e:
        pass

if __name__ == "__main__":
    try:
        sentiment_analysis_pipeline.with_options(
            settings=pipeline_settings,
        )()
    finally:
        cleanup_otel()
        time.sleep(0.5)
```