---
description: Reading from a continuously changing datasource
---

# Import dynamic data

If you want to see the code for this chapter of the guide, head over to the 
[GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide/chapter\_6.py).

## Import data from a dynamic data source

Until now, we've been reading from a static data importer step because we are at the experimentation phase of the ML 
workflow. Now as we head towards production, we want to switch over to a non-static, dynamic data importer step:

This could be anything like:

* A database/data warehouse that updates regularly (SQL databases, BigQuery, Snowflake)
* A data lake (S3 Buckets/Azure Blob Storage/GCP Storage)
* An API which allows you to query the latest data.

### Read from a dynamic datasource

Let's also slightly change our pipeline to add our new step. For this guide, we have set up a Mock API that simulates 
a real world setting of reading from an external API. The data in the API is just MNIST data but new data is added 
every day, and we query the new data each time the pipeline runs.

```python
import numpy as np
import pandas as pd
import requests

from zenml.steps import step, BaseStepConfig, Output


class ImporterConfig(BaseStepConfig):
    n_days: int = 1


def get_X_y_from_api(n_days: int = 1, is_train: bool = True):
    url = (
        "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_train.json"
        if is_train
        else "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_test.json"
    )
    df = pd.DataFrame(requests.get(url).json())
    X = df["image"].map(lambda x: np.array(x)).values
    X = np.array([x.reshape(28, 28) for x in X])
    y = df["label"].map(lambda y: np.array(y)).values
    return X, y


@step
def dynamic_importer(
    config: ImporterConfig,
) -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Downloads the latest data from a mock API."""
    X_train, y_train = get_X_y_from_api(n_days=config.n_days, is_train=True)
    X_test, y_test = get_X_y_from_api(n_days=config.n_days, is_train=False)
    return X_train, y_train, X_test, y_test
```

And then change the pipeline run as follows:

```python
scikit_p = mnist_pipeline(
    importer=dynamic_importer(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(),
    evaluator=sklearn_evaluator(),
)
```

### Run

You can run this as follows:

```python
python chapter_6.py
```

### Inspect

Even if our data originally lives in an external API, we have now downloaded it and versioned locally as we ran 
this pipeline. So we can fetch it and inspect it:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
print(f"Pipeline `mnist_pipeline` has {len(p.runs)} run(s)")
eval_step = p.runs[-1].get_step("evaluator")
val = eval_step.output.read()
print(f"We scored an accuracy of {val} on the latest run!")
```

You will get the following output:

```bash
Pipeline `mnist_pipeline` has 1 run(s)
We scored an accuracy of 0.72 on the latest run!
```

Now we are loading data dynamically from a continuously changing data source!

{% hint style="info" %}
In the near future, ZenML will help you automatically detect drift and schema changes across pipeline runs, to make 
your pipelines even more robust! Keep an eye out on this space and future releases!
{% endhint %}
