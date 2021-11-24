# Visualize statistics
This examples show-cases the built-in `FacetStatisticsVisualizer` using the [Facets Overview](https://pypi.org/project/facets-overview/) integration.
[Facets](https://pair-code.github.io/facets/) is an awesome project that helps users visualize large amounts of data in a coherent way.

## Visualizers
Visualizers are Python classes that take post-execution view objects (e.g. `PipelineView`, `PipelineRunView`, `StepView`, etc.) and create 
visualizations for them. ZenML will support many standard ones but one can always extend them using the `BaseVisualization` classes.

## Overview
Here, we are using the [Boston Housing Price Regression](https://keras.io/api/datasets/boston_housing/) dataset. We create a simple pipeline that 
returns two pd.DataFrames, one for the training data and one for the test data. In the post-execution workflow we then plug in the visualization class 
that visualizes the statistics of these dataframes for us. 

This visualization is produced with the following code:

```python
from zenml.core.repo import Repository
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)

repo = Repository()
pipe = repo.get_pipelines()[-1]
importer_outputs = pipe.runs[-1].get_step(name="importer")
FacetStatisticsVisualizer().visualize(importer_outputs)
```

It produces the following visualization:

![Statistics for boston housing dataset](../../../docs/book/.gitbook/assets/statistics_boston_housing.png)



## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml tensorflow facets-overview

# pull example
zenml example pull visualizers
cd zenml_examples/visualizers/statistics

# initialize
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```

### Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
