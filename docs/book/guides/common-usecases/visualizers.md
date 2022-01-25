---
description: An image speaks a thousand words.
---

# Visualizers

## What is a visualizer

Sometimes it makes sense in the [post-execution workflow](post-execution-workflow.md) to actually visualize step outputs.

## Examples of visualizations

### Lineage with [dash](https://plotly.com/dash/)

```python
from zenml.repository import Repository
from zenml.integrations.dash.visualizers.pipeline_run_lineage_visualizer import (
    PipelineRunLineageVisualizer,
)

repo = Repository()
latest_run = repo.get_pipelines()[-1].runs[-1]
PipelineRunLineageVisualizer().visualize(latest_run)
```

It produces the following visualization:

![Lineage Diagram](../../assets/zenml-pipeline-run-lineage-dash.png)

### Statistics with [Facets](https://github.com/PAIR-code/facets)

```python
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)

FacetStatisticsVisualizer().visualize(output)
```

It produces the following visualization:

![Statistics for boston housing dataset](../../assets/statistics-boston-housing.png)

### Distributions with [whylogs](https://github.com/whylabs/whylogs)

```python
repo = Repository()
pipe = repo.get_pipelines()[-1]
whylogs_outputs = pipe.runs[-1].get_step(name=step_name)
WhylogsVisualizer().visualize(whylogs_outputs)
```

It produces the following visualization:

![WhyLogs visualization](../../assets/whylogs/whylogs-visualizer.png)

### Drift with [evidently](https://github.com/evidentlyai/evidently)

```python
from zenml.integrations.evidently.visualizers import EvidentlyVisualizer

repo = Repository()
pipe = repo.get_pipelines()[-1]
evidently_outputs = pipe.runs[-1].get_step(name="drift_detector")
EvidentlyVisualizer().visualize(evidently_outputs)
```

It produces the following visualization:

![Evidently Drift Detection](../../assets/evidently/drift_visualization.png)