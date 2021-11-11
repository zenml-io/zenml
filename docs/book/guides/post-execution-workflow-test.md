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


### Define standard ML steps

```python
@trainer
def trainer(dataset: torch.Dataset) -> torch.nn.Module:
   ... 
   return model
```



### Get pipelines and runs

```python
pipelines = repo.get_pipelines()   # get all pipelines from all stacks
pipeline = repo.get_pipeline(pipeline_name=..., stack_key=...)
```

```python
runs = pipeline.get_runs()  # all runs of a pipeline chronlogically ordered
run = runs[-1]  # latest run
output = step.outputs[0]  # get outputs
```

### Materializing outputs (or inputs)

Once an output artifact is acquired from history, one can visualize it with any chosen `Materializer`.

```python
df = output.read(materializer=PandasMaterializer)  # get data

```

### Seeing statistics and schema

```python
stats = output.read(materializer=StatisticsMaterializer)  # get stats
schema = output.read(materializer=SchemaMaterializer)  # get schema
```

### Retrieving Model

```python
model = output.read(materializer=KerasModelMaterializer)  # get model
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


# will get you the value from the original materializer used in the pipeline
output.read()  
```

## Visuals


