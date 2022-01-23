# Post Execution Workflow

## Post-execution workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

## Component Hierarchy

In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```bash
repository -> pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

### Repository

The highest level `repository` object is where to start from.

```python
from zenml.repository import Repository

repo = Repository()
```

#### Pipelines

```python
# get all pipelines from all stacks
pipelines = repo.get_pipelines()  

# or get one pipeline by name and/or stack key
pipeline = repo.get_pipeline(pipeline_name=..., stack_key=...)
```

#### Runs

```python
runs = pipeline.runs  # all runs of a pipeline chronlogically ordered
run = runs[-1]  # latest run

# or get it by name
run = pipeline.get_run(run_name="custom_pipeline_run_name")
```

#### Steps

```python
# at this point we switch from the `get_` paradigm to properties
steps = run.steps  # all steps of a pipeline
step = steps[0]
print(step.entrypoint_name)
```

#### Outputs

```python
# The outputs of a step
# if multiple outputs they are accessible by name
outputs = step.outputs["output_name"]

# if one output, use the `.output` property instead 
output = step.output 

# will get you the value from the original materializer used in the pipeline
output.read()  
```

### Materializing outputs (or inputs)

Once an output artifact is acquired from history, one can visualize it with any chosen `Visualizer`.

```python
from zenml.materializers import PandasMaterializer


df = output.read(materializer_class=PandasMaterializer)
df.head()
```

### Retrieving Model

```python
from zenml.integrations.tensorflow.materializers.keras_materializer import KerasMaterializer    


model = output.read(materializer_class=KerasMaterializer)
model  # read keras.Model
```

## Visuals

### Seeing statistics

```python
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)

FacetStatisticsVisualizer().visualize(output)
```

It produces the following visualization:

![Statistics for boston housing dataset](../../.gitbook/assets/statistics\_boston\_housing.png)
