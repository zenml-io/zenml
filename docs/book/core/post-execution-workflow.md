# Post Execution Workflow

## Post-execution workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page captures these workflows at an orbital level.

## Component Hierarchy

In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```python
pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

The highest level `pipeline` object is also related to the `stack` component implicitly.

### Hierarchy in Code

#### Pipelines

```python
pipelines = repo.get_pipelines()  # get all pipeline, can be filtered by name etc via params
pipeline = pipeline[0]
```

#### Runs

```python
runs = pipeline.get_runs()  # all runs of a pipeline, can be filtered by name etc.
run = runs[0]
```

#### Steps

```python
# at this point we switch from the `get_` paradigm to properties
steps = run.steps  # all steps of a pipeline
step = steps[0] || steps.step_name
```

#### Outputs

```python
outputs = step.outputs # all outputs of a step: these are all Artifacts
output = outputs.text_artifact_name  # artifact output

>>> output.type_ 
TextArtifact
>> output.materializers

# OR
output = outputs[0]  # basic output
>> output.type_
int
>> output.value
4
```

## Visuals

### Materializing outputs \(or inputs\)

Once an output\_artifact is acquired from history, one can visualize it with any chosen `Materializer`.

```python
df = output.materializers.pandas.read() # can Read TextArtifact into Pandas DF
df.head()
```

### Seeing statistics and schema

```python
stats = output.materializers.statistics.read()
stats  # visualize facet

schema = output.materializers.schema.read()
schema # visualize schema
```

### Retrieving Model

```python
model = output.materializers.keras.read()
model  # visualize facet
```

## Comparing Runs \[In Progress\]

