---
description: Switching orchestrators to run in the cloud
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Switching orchestration

It is common to need to switch out the ways you run your pipelines as you
progress through your work. When you start out, a local orchestrator is all you
need: you run your pipelines on small slices of your data and you build out your
pipeline incrementally. At a certain point, it might make sense to scale up the
load, or to run it on something closer to what your final 'production' stack
will resemble. Switching your orchestrator is a matter of a single CLI command.

Let's take a look at how you would do this. We can start off with a very simple
pipeline, one that loads a DataFrame and returns it:

```python
import random

import pandas as pd

from zenml.pipelines import pipeline
from zenml.steps import step


@step
def get_dataframe() -> pd.DataFrame:
    """Returns a DataFrame filled with random numbers."""
    return pd.DataFrame(
        {
            "a": [random.random() for _ in range(100)],
            "b": [random.random() for _ in range(100)],
        }
    )


@pipeline
def test_pipeline(get_dataframe) -> None:
    """Pipeline to get a simple DataFrame."""
    get_dataframe()


test_pipeline(get_dataframe=get_dataframe()).run()
```

When we start out, we'll be using the default stack which includes a default
orchestrator. You can see how this is all configured with the following CLI
command:

```shell
zenml stack describe default
```

Now that we see that it's working, we might already know that our stack will
require a certain orchestrator, the Airflow orchestrator for example. Running
our pipeline on Airflow is a simple matter of installing the integration,
creating the new stack, then switching our stack:

```shell
zenml integration install airflow
zenml orchestrator register airflow_orchestrator --flavor=airflow
zenml stack register airflow_stack -a default -o airflow_orchestrator --set
zenml stack up
```

Once our Airflow stack is up and running, we can run our pipeline again with `python
run.py` and we can rerun on the new orchestrator. Switching out all the other
pieces of your ZenML infrastructure is just as easy. Simple CLI commands gives
you the flexibility to switch between different components, and the underlying
code doesn't need to change at all!

{% hint style="info" %}
To read a more detailed guide about how Orchestrators function in ZenML,
[click here](../../component-gallery/orchestrators/orchestrators.md).
{% endhint %}