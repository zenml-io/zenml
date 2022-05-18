---
description: Best Practices, Recommendations, and Tips from the ZenML team.
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

#### Pass requirements to your pipelines through the decorator:

```python
from zenml.integrations.constants import TENSORFLOW
from zenml.pipelines import pipeline

@pipeline(required_integrations=[TENSORFLOW])
def training_pipeline():
    ...
```

Writing your pipeline like this makes sure you can change out the orchestrator
at any point without running into dependency issues.

#### Nest `pipeline_instance.run()` in `if __name__ == "__main__"`

```python
pipeline_instance = training_pipeline(...)

if __name__ == "__main__":
    pipeline_instance.run()
```

This ensures that loading the pipeline from elsewhere does not also run it.

#### Don't use the same metadata stores across multiple artifact stores

You might run into issues as the metadata store will point to artifacts in
inactive artifact stores.

#### Never call the pipeline instance `pipeline` or a step instance `step`

This will overwrite the imported `pipeline` and `step` decorators.

#### Use profiles to manage stacks


#### Use unique pipeline names across projects, especially if used with the same metadata store

Pipeline names are their unique identifiers, so using the same name for
different pipelines will create a mixed history of runs between the two 
pipelines.

#### Check which integrations are required for registering a stack component 

You can do so by running `zenml flavor list` and installing the integration(s) 
if missing with `zenml integration install`.

#### Initialize the ZenML repository in the root of the source code tree of a project, even if it's optional

This will set the zenml project root for the project and ...

#### Put your runners in the root of the repository

#### Enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior

#### Include a `.dockerignore` in the ZenML repository to exclude files and folders from the container images built by ZenML for containerized environments, like Kubeflow and some step operators

#### Use `get_pipeline_run(RUN_NAME)` instead of indexing (`[-1]`) into the full list of pipeline runs

#### Explicitly disable caching when loading data from filesystem or external APIs

#### Have your imports relative to your `.zen` directory OR have your imports relative to the root of your repository in cases when you don't have a `.zen` directory (=> which means to have the runner at the root of your repository)

#### Do not overlap `required_integrations` and `requirements`

#### Explicity set `enable_cache` at the `@pipeline` level

## Tips

* Use `zenml GROUP explain` to explain what everything is
* Run `zenml stack up` after switching stacks (but this is also enforced by validations that check if the stack is up)

For a practical example on all of the above, please check out [ZenFiles](https://github.com/zenml-io/zenfiles) which are practical end-to-end projects built using ZenML.
