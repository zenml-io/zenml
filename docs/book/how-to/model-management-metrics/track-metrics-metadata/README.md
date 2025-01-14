---
icon: ufo-beam
description: Tracking and comparing metrics and metadata
---

# Track metrics and metadata

ZenML provides a unified way to log and manage metrics and metadata through the `log_metadata` function. This versatile function allows you to log metadata across various entities like models, artifacts, steps, and runs through a single interface. Additionally, you can adjust if you want to automatically log the same metadata for related entities.

## Logging Metadata

### The most basic use-case

You can use the `log_metadata` function within a step:

```python
from zenml import step, log_metadata

@step
def my_step() -> ...:
    log_metadata(metadata={"accuracy": 0.91})
    ...
```

This will log the `accuracy` for the step, its pipeline run, and if provided its model version.

### A real-world example

Here's a more comprehensive example showing how to log various types of metadata in a machine learning pipeline:

```python
from zenml import step, pipeline, log_metadata

@step
def process_engine_metrics() -> float:
    # does some machine learning things

    # Log operational metrics
    log_metadata(
        metadata={
            "engine_temperature": 3650,  # Kelvin
            "fuel_consumption_rate": 245,  # kg/s
            "thrust_efficiency": 0.92,
        }
    )
    return 0.92

@step
def analyze_flight_telemetry(efficiency: float) -> None:
    # does some more machine learning things

    # Log performance metrics
    log_metadata(
        metadata={
            "altitude": 220000,  # meters
            "velocity": 7800,  # m/s
            "fuel_remaining": 2150,  # kg
            "mission_success_prob": 0.9985,
        }
    )

@pipeline
def telemetry_pipeline():
    efficiency = process_engine_metrics()
    analyze_flight_telemetry(efficiency)
```

This data can be visualized and compared in the ZenML Pro dashboard. The
illustrations below show the data from this example in the ZenML Pro dashboard
using the Experiment Comparison tool.

## Visualizing and Comparing Metadata (Pro)

Once you've logged metadata in your pipelines, you can use ZenML's Experiment Comparison tool to analyze and compare metrics across different runs. This feature is available in the ZenML Pro dashboard.

<div style="position: relative; padding-bottom: 65.81352833638026%; height: 0;"><iframe src="https://www.loom.com/embed/693b2d829600492da7cd429766aeba6a?sid=007c88b1-ffd4-4a75-a575-4a474ee7e0c9" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>

### Comparison Views

The Experiment Comparison tool offers two complementary views for analyzing your pipeline metadata:

1. **Table View**: Compare metadata across runs with automatic change tracking
   ![Table View](../../../../.gitbook/assets/table-view.png)

2. **Parallel Coordinates Plot**: Visualize relationships between different metrics
   ![Parallel Coordinates](../../../../.gitbook/assets/coordinates-view.png)

The tool lets you compare up to 20 pipeline runs simultaneously and supports any
numerical metadata (`float` or `int`) that you've logged in your pipelines.

### Additional use-cases

The `log_metadata` function supports various use-cases by allowing you to specify the target entity (e.g., model, artifact, step, or run) with flexible parameters. You can learn more about these use-cases in the following pages:

- [Log metadata to a step](attach-metadata-to-a-step.md)
- [Log metadata to a run](attach-metadata-to-a-run.md)
- [Log metadata to an artifact](attach-metadata-to-an-artifact.md)
- [Log metadata to a model](attach-metadata-to-a-model.md)

{% hint style="warning" %}
The older methods for logging metadata to specific entities, such as `log_model_metadata`, `log_artifact_metadata`, and `log_step_metadata`, are now deprecated. It is recommended to use `log_metadata` for all future implementations.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
