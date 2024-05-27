# Build the pipeline without running

Pipeline builds are usually done implicitly when you run a pipeline on a docker-based orchestrator. But you are also able to just build a pipeline without running this. To do this you simply do this:

```python
from zenml import pipeline

@pipeline
def my_pipeline(...):
    ...

my_pipeline.build()
```

You can see all pipeline builds with the command:

This will register the build output in the ZenML database and allow you to use the built images when running a pipeline later.

```bash
zenml pipeline builds list
```

To use a registered build when running a pipeline, pass it as an argument in Python

```python
my_pipeline = my_pipeline.with_options(build=<BUILD_ID>)
```

or when running a pipeline from the CLI

```bash
zenml pipeline run <PIPELINE_NAME> --build=<BUILD_ID>
```
