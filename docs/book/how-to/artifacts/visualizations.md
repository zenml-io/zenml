---
description: >-
  Learn how to visualize the data artifacts produced by your ZenML pipelines.
---

# Visualizing Artifacts

Data visualization is a powerful tool for understanding your ML pipeline outputs. ZenML provides built-in capabilities to visualize artifacts, helping you gain insights into your data, model performance, and pipeline execution.

## Automatic Visualizations

ZenML automatically generates visualizations for many common data types, making it easy to inspect your artifacts without additional code.

### Dashboard Visualizations

The ZenML dashboard displays visualizations for artifacts produced by your pipeline runs:

![ZenML Artifact Visualizations](../../../.gitbook/assets/artifact_visualization_dashboard.png)

To view visualizations in the dashboard:

1. Navigate to the **Runs** tab
2. Select a specific pipeline run
3. Click on any step to view its outputs
4. Select an artifact to view its visualizations

### Notebook Visualizations

You can also display artifact visualizations in Jupyter notebooks using the `visualize()` method:

```python
from zenml.client import Client

# Get an artifact from a previous pipeline run
run = Client().get_pipeline_run("<PIPELINE_RUN_ID>")
artifact = run.get_artifact("<STEP_NAME>")

# Display the visualization
artifact.visualize()
```

## Supported Visualization Types

ZenML supports visualizations for many common data types out of the box:

### Pandas DataFrames and Series

Pandas DataFrames are visualized as interactive tables with statistical summaries:

```python
@step
def create_dataframe() -> pd.DataFrame:
    df = pd.DataFrame({
        'A': np.random.randn(100),
        'B': np.random.randn(100),
        'C': np.random.randn(100)
    })
    return df
```

### NumPy Arrays

NumPy arrays are visualized based on their dimensionality:
- 1D arrays: Histograms or line plots
- 2D arrays: Heatmaps or scatter plots
- 3D arrays: Multiple 2D visualizations or interactive 3D plots

### Images

Image data (PNG, JPEG, etc.) is displayed directly:

```python
from PIL import Image
import numpy as np

@step
def generate_image() -> Image.Image:
    # Create a random image
    array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    img = Image.fromarray(array)
    return img
```

### Matplotlib Figures

Matplotlib figures are rendered directly:

```python
import matplotlib.pyplot as plt

@step
def create_plot() -> plt.Figure:
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
    ax.set_title('Sample Plot')
    return fig
```

### Integration-Specific Visualizations

Many ZenML integrations provide specialized visualizations:

#### Evidently Reports

Data drift and quality reports from [Evidently](https://docs.zenml.io/stacks/data-validators/evidently) are displayed as interactive HTML:

```python
from evidently.report import Report
from evidently.metrics import DataDriftTable

@step
def create_drift_report(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame
) -> Report:
    report = Report(metrics=[DataDriftTable()])
    report.run(reference_data=reference_data, current_data=current_data)
    return report
```

#### Hugging Face Datasets

[Hugging Face](https://zenml.io/integrations/huggingface) datasets are visualized using an interactive dataset viewer:

![Hugging Face Dataset Viewer](../../../.gitbook/assets/artifact_visualization_huggingface.gif)

#### Other Integrations

- [WhyLogs](https://docs.zenml.io/stacks/data-validators/whylogs) profiles
- [Great Expectations](https://docs.zenml.io/stacks/data-validators/great-expectations) validation results
- Confusion matrices and performance metrics
- And many more!

## Creating Custom Visualizations

You can create custom visualizations for your artifacts by implementing a custom Visualizer:

```python
from zenml.enums import ArtifactType
from zenml.visualizers import BaseVisualizer
import matplotlib.pyplot as plt
import io
import base64

class CustomDataVisualizer(BaseVisualizer):
    ASSOCIATED_TYPES = (CustomData,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def visualize(self, data: CustomData) -> List[Dict[str, Any]]:
        # Create a matplotlib figure
        fig, ax = plt.subplots()
        ax.plot(data.x, data.y)
        ax.set_title('Custom Data Visualization')
        
        # Convert figure to PNG
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        # Return visualization metadata
        return [{
            "type": "image",
            "format": "png",
            "data": image_base64,
            "title": "Custom Visualization"
        }]
```

Register your visualizer:

```python
from zenml.integrations.registry import integration_registry

def register_my_visualizers():
    from my_custom_visualizers import CustomDataVisualizer
    integration_registry.visualizers[CustomData] = CustomDataVisualizer
```

### Visualization Types

ZenML supports several visualization formats:

- **Image**: PNG, JPEG, or other image formats
- **HTML**: Interactive HTML elements
- **Markdown**: Formatted text with markup
- **JSON**: Structured data for custom rendering
- **Text**: Plain text outputs

## Controlling Visualizations

### Enabling/Disabling Visualizations

You can control whether visualizations are generated at the pipeline or step level:

```python
# Disable visualizations for a pipeline
@pipeline(enable_artifact_visualization=False)
def my_pipeline():
    ...

# Disable visualizations for a step
@step(enable_artifact_visualization=False)
def my_step():
    ...
```

You can also configure this in YAML:

```yaml
enable_artifact_visualization: False

steps:
  my_step:
    enable_artifact_visualization: True
```

### Visualization in Production

For production environments where visualization may add overhead, you can disable visualizations globally:

```bash
export ZENML_DISABLE_ARTIFACT_VISUALIZATION=True
```

Or in your ZenML configuration:

```python
# In your zenml_config.py
disable_artifact_visualization = True
```

## Best Practices

1. **Be selective**: Generate visualizations for key insights, not everything
2. **Consider performance**: Complex visualizations can slow down pipeline execution
3. **Use appropriate formats**: Choose the right format for your data (e.g., HTML for interactive content)
4. **Provide context**: Add titles, labels, and descriptions to make visualizations more understandable
5. **Build for scale**: Create visualizations that work well with both small and large datasets

## Conclusion

Visualizing artifacts is a powerful way to gain insights from your ML pipelines. ZenML's built-in visualization capabilities make it easy to understand your data and model outputs, identify issues, and communicate results.

By leveraging these visualization tools, you can better understand your ML workflows, debug problems more effectively, and make more informed decisions about your models.

For more advanced artifact management patterns, see [Complex Use Cases](./complex_use_cases.md). 