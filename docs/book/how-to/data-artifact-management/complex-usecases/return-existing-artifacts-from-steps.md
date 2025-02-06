---
description: Return existing artifacts from steps.
---

# Return existing artifacts from steps

ZenML allows you to return existing artifact versions that are already registered in the ZenML server from your pipeline steps. This is particularly useful when you want to optimize caching behavior in your pipelines.

## Understanding caching behavior

ZenML's caching mechanism uses the IDs of the step input artifacts (among other things) to determine whether a step needs to be re-run or can be cached. By default, when a step produces an output artifact, a new artifact version is registered - even if the output data is identical to a previous run.

This means that steps downstream of a non-cached step will also need to be re-run, since their input artifact IDs will be different, even if the underlying data hasn't changed. To enable better caching, you can return existing artifact versions from your steps instead of always creating new ones. This is useful if you want to do some computation in early parts of the pipeline that decides whether the remaining steps of the pipeline can be cached.

```python
from zenml import pipeline, step, log_metadata
from zenml.client import Client
from typing import Annotated

# We want to always run this step to decide whether the
# downstream steps can be cached, so we disable caching for it
@step(enable_cache=False)
def compute_cache() -> Annotated[int, "cache_key"]:
    # Replace this with your custom logic, for example compute a key
    # from the date of the latest avaialable data point
    cache_key = 27

    artifact_versions = Client().list_artifact_versions(
        sort_by="desc:created",
        size=1,
        name="cache_key",
        run_metadata={"cache_key_value": cache_key},
    )

    if artifact_versions:
        return artifact_versions[0]
    else:
        # Log the cache key as metadata on the artifact version so we easily
        # fetch it later in subsequent runs
        log_metadata(metadata={"cache_key_value": cache_key}, infer_artifact=True)
        return cache_key


@step
def downstream_step(cache_key: int):
    ...

# Enable caching for the pipeline
@pipeline(enable_cache=True)
def my_pipeline():
    cache_key = compute_cache()
    downstream_step(cache_key)
```


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
