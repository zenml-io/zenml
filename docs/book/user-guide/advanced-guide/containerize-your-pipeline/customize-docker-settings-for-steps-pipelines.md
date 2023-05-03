---
description: Learn how to customize the docker settings and requirements .
---

# Customize docker settings for steps/pipelines

By default the exact same docker image is used for each step.



```python
docker_settings = DockerSettings(requirements=["tensorflow"])

@pipeline(settings={"docker": docker_settings})
def my_training_pipeline(...):
    ...
```

You can also specify specialized settings for all the steps of your pipeline. Values specified for a step will override the values defined on the pipeline that the step is contained in and can be used to build specialized images.
