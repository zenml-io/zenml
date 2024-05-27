# Build the pipeline without running

Pipeline builds are usually done implicitly when you run a pipeline on a docker-based orchestrator. But you are also able to just build a pipeline without running this. To do this you simply do this:

```python
from zenml import pipeline

@pipeline
def my_pipeline(...):
    ...

my_pipeline.build()
```

You can find a list of builds for your pipeline through the ZenML CLI:

```python
zenml pipeline builds list
```
