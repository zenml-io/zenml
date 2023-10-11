---
description: Best practices, recommendations, and tips from the ZenML team
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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
├── Dockerfile
├── README.md
├── requirements.txt
├── run.py
└── setup.sh
```

## Best Practices and Tips

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
external APIs or file systems, caching should be disabled explicitly for the 
step.

### Enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior

Cache is implicitly disabled for steps that have a
[context](../advanced-guide/pipelines/step-metadata.md) argument,
because it is assumed that you might use the step context to retrieve artifacts
from the artifact store that are unrelated to the current step. However, if that
is not the case, and your step logic doesn't invalidate the caching behavior, it
would be better to explicitly enable the cache for your step.

### Use unique pipeline names across projects/workspaces

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

### Use `get_pipeline(pipeline=...)` instead of indexing (`[0]`) to retrieve previous pipelines

When [inspecting pipeline runs](../starter-guide/pipelines/pipelines.md)
it is tempting to access the pipeline views directly by their index, but
the pipelines are sorted in descending order of their creation time, so the 
pipeline at `[0]` might not be the one you are expecting.

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

For a practical example on all of the above, please check
out [ZenML Projects](https://github.com/zenml-io/zenml-projects) which are practical
end-to-end projects built using ZenML.
