---
description: Best practices, recommendations, and tips from the ZenML team
---

## Recommended Repository Structure

```
├── notebooks                   <- All notebooks in one place
│   ├── *.ipynb         
├── pipelines                   <- All pipelines in one place
│   ├── training_pipeline
│   │   ├── .dockerignore
│   │   ├── config.yaml
│   │   ├── Dockerfile
│   │   ├── training_pipeline.py
│   │   ├── requirements.txt
│   ├── deployment_pipeline
│   │   ├── ...
├── steps                       <- All steps in one place
│   ├── loader_step
│   │   ├── loader_step.py
│   ├── training_step
│   │   ├── ...
├── .dockerignore 
├── .gitignore
├── config.yaml
├── Dockerfile
├── README.md
├── requirements.txt
├── run.py
└── setup.sh
```

## Best Practices and Tips

### Pass integration requirements to your pipelines through the decorator:

```python
from zenml.integrations.constants import TENSORFLOW
from zenml.pipelines import pipeline


@pipeline(required_integrations=[TENSORFLOW])
def training_pipeline():
    ...
```

Writing your pipeline like this makes sure you can change out the orchestrator
at any point without running into dependency issues.

### Do not overlap `required_integrations` and `requirements`

Setting requirements twice can lead to unexpected behavior as you will end up
with *only* one of the two defined package versions, which might cause problems.

### Nest `pipeline_instance.run()` in `if __name__ == "__main__"`

```python
pipeline_instance = training_pipeline(...)

if __name__ == "__main__":
    pipeline_instance.run()
```

This ensures that loading the pipeline from elsewhere does not also run it.

### Never call the pipeline instance `pipeline` or a step instance `step`

Doing this will overwrite the imported `pipeline` and `step` decorators and lead
to failures at later stages if more steps and pipelines are decorated there.

```python
from zenml.pipelines import pipeline


@pipeline
def first_pipeline():
    ...


pipeline = first_pipeline(...)


@pipeline  # The code will fail here
def second_pipeline():
    ...
```

### Explicitly set `enable_cache` at the `@pipeline` level

Caching is enabled by default for ZenML Pipelines. It is good to be explicit,
 though, so that it is clear when looking at the code if caching is enabled or
disabled for any given pipeline.

### Explicitly disable caching when loading data from filesystem or external APIs

ZenML inherently uses caching. However, this caching relies on changes of input
artifacts to invalidate the cache. In case a step has external data sources like
external APIs or filesystems, caching should be disabled explicitly for the 
step.

### Enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior

Cache is implicitly disabled for steps that have a
[context](../developer-guide/advanced-usage/step-fixtures.md#step-contexts) argument,
because it is assumed that you might use the step context to retrieve artifacts
from the artifact store that are unrelated to the current step. However, if that
is not the case, and your step logic doesn't invalidate the caching behavior, it
would be better to explicitly enable the cache for your step.

### Don't use the same metadata stores across multiple artifact stores

You might run into issues as the metadata store will point to artifacts in
inactive artifact stores.

### Use unique pipeline names across projects, especially if used with the same metadata store

Pipeline names are their unique identifiers, so using the same name for
different pipelines will create a mixed history of runs between the two
pipelines.

### Check which integrations are required for registering a stack component

You can do so by running `zenml flavor list` and installing the missing integration(s) 
with `zenml integration install`.

### Initialize the ZenML repository in the root of the source code tree of a project, even if it's optional

This will set the ZenML project root for the project and create a local
configuration. The advantage is that you create and maintain your active stack
on a project level.

### Include a `.dockerignore` in the ZenML repository to exclude files and folders from the container images built by ZenML for containerized environments

Containerized Orchestrators and Step Operators load your complete project files 
into a Docker image for execution. To speed up the process and reduce Docker 
image sizes, exclude all unnecessary files (like data, virtual environments, 
git repos, etc.) within the `.dockerignore`.

### Use `get_pipeline(pipeline=...)` instead of indexing (`[-1]`) to retrieve previous pipelines

When [inspecting pipeline runs](../developer-guide/steps-pipelines/inspecting-pipeline-runs.md)
it is tempting to access the pipeline views directly by their index, but
the pipelines within your `Repository` are sorted by time of first run, so the 
pipeline at `[-1]` might not be the one you are expecting.

```python
from zenml.post_execution import get_pipeline

first_pipeline.run()
second_pipeline.run()
first_pipeline.run()

get_pipelines()
>>> [PipelineView('first_pipeline'), PipelineView('second_pipeline')]

# This is the recommended explicit way to retrieve your specific pipeline 
# using the pipeline class if you have it at hand
get_pipeline(pipeline=first_pipeline)

# Alternatively you can also use the name of the pipeline
get_pipeline(pipeline="first_pipeline")
```

### Have your imports relative to your `.zen` directory OR have your imports relative to the root of your repository in cases when you don't have a `.zen` directory (=> which means to have the runner at the root of your repository)

ZenML uses the `.zen` repository root to resolve the class path of your 
functions and classes in a way that is portable across different types of 
environments such as containers. If a repository is not present, the location 
of the main Python module is used as an implicit repository root.

### Put your runners in the root of the repository

Putting your pipeline runners in the root of the repository ensures that all
imports that are defined relative to the project root resolve for the pipeline runner.

## Tips

* Use `zenml GROUP explain` to explain what everything is
* Run `zenml stack up` after switching stacks (but this is also enforced by
  validations that check if the stack is up)

For a practical example on all of the above, please check
out [ZenFiles](https://github.com/zenml-io/zenfiles) which are practical
end-to-end projects built using ZenML.
