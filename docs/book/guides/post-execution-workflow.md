# Post Execution Workflow

## Post-execution workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page captures these workflows at an orbital level.

## Component Hierarchy


In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```bash
repository -> pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

### Repository

The highest level `repository` object is where to start from.

```python
from zenml.core.repo import Repository

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
runs = pipeline.get_runs()  # all runs of a pipeline chronlogically ordered
run = runs[-1]  # latest run
```

#### Steps

```python
# at this point we switch from the `get_` paradigm to properties
steps = run.steps  # all steps of a pipeline
step = steps[0] 
print(step.name)
```

#### Outputs

```python
# all outputs of a step
# if one output, then its the first element in the list
# if multiple output, then in the order defined with the `Output`
outputs = step.outputs 
output = outputs[0]

# will get you the value from the original materializer used in the pipeline
output.read()  
```

## Visuals

### Materializing outputs (or inputs)

Once an output artifact is acquired from history, one can visualize it with any chosen `Materializer`.

```python
df = output.read(materializer=PandasMaterializer)
df.head()
```

### Seeing statistics and schema

```python
stats = output.read(materializer=StatisticsMaterializer)
stats  # visualize stats

schema = output.read(materializer=SchemaMaterializer)
schema # visualize schema
```

### Retrieving Model

```python
model = output.read(materializer=KerasModelMaterializer)
model  # visualize model
```
