---
description: Managing data in Feast feature stores.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Feast

Feast (Feature Store) is an operational data system for managing and serving machine learning features to models in production. Feast is able to serve feature data to models from a low-latency online store (for real-time prediction) or from an offline store (for scale-out batch scoring or model training).

### When would you want to use it?

There are two core functions that feature stores enable:

* access to data from an offline / batch store for training.
* access to online data at inference time.

Feast integration currently supports your choice of offline data sources and a [Redis](https://redis.com/) backend for your online feature serving. We encourage users to check out [Feast's documentation](https://docs.feast.dev/) and [guides](https://docs.feast.dev/how-to-guides/) on how to set up your offline and online data sources via the configuration `yaml` file.

{% hint style="info" %}
COMING SOON: While the ZenML integration has an interface to access online feature store data, it currently is not usable in production settings with deployed models. We will update the docs when we enable this functionality.
{% endhint %}

### How to deploy it?

ZenML assumes that users already have a Feast feature store that they just need to connect with. If you don't have a feature store yet, follow the [Feast Documentation](https://docs.feast.dev/how-to-guides/feast-snowflake-gcp-aws/deploy-a-feature-store) to deploy one first.

To use the feature store as a ZenML stack component, you also need to install the corresponding `feast` integration in ZenML:

```shell
zenml integration install feast
```

Now you can register your feature store as a ZenML stack component and add it into a corresponding stack:

```shell
zenml feature-store register feast_store --flavor=feast --feast_repo="<PATH/TO/FEAST/REPO>"
zenml stack register ... -f feast_store
```

### How do you use it?

{% hint style="warning" %}
Online data retrieval is possible in a local setting, but we don't currently support using the online data serving in the context of a deployed model or as part of model deployment. We will update this documentation as we develop this feature.
{% endhint %}

Getting features from a registered and active feature store is possible by creating your own step that interfaces into the feature store:

```python
from datetime import datetime
from typing import Any, Dict, List, Union
import pandas as pd

from zenml import step
from zenml.client import Client


@step
def get_historical_features(
    entity_dict: Union[Dict[str, Any], str],
    features: List[str],
    full_feature_names: bool = False
) -> pd.DataFrame:
    """Feast Feature Store historical data step

    Returns:
        The historical features as a DataFrame.
    """
    feature_store = Client().active_stack.feature_store
    if not feature_store:
        raise DoesNotExistException(
            "The Feast feature store component is not available. "
            "Please make sure that the Feast stack component is registered as part of your current active stack."
        )

    params.entity_dict["event_timestamp"] = [
        datetime.fromisoformat(val)
        for val in entity_dict["event_timestamp"]
    ]
    entity_df = pd.DataFrame.from_dict(entity_dict)

    return feature_store.get_historical_features(
        entity_df=entity_df,
        features=features,
        full_feature_names=full_feature_names,
    )


entity_dict = {
    "driver_id": [1001, 1002, 1003],
    "label_driver_reported_satisfaction": [1, 5, 3],
    "event_timestamp": [
        datetime(2021, 4, 12, 10, 59, 42).isoformat(),
        datetime(2021, 4, 12, 8, 12, 10).isoformat(),
        datetime(2021, 4, 12, 16, 40, 26).isoformat(),
    ],
    "val_to_add": [1, 2, 3],
    "val_to_add_2": [10, 20, 30],
}


features = [
    "driver_hourly_stats:conv_rate",
    "driver_hourly_stats:acc_rate",
    "driver_hourly_stats:avg_daily_trips",
    "transformed_conv_rate:conv_rate_plus_val1",
    "transformed_conv_rate:conv_rate_plus_val2",
]

@pipeline
def my_pipeline():
    my_features = get_historical_features(entity_dict, features)
    ...
```

{% hint style="warning" %}
Note that ZenML's use of Pydantic to serialize and deserialize inputs stored in the ZenML metadata means that we are limited to basic data types. Pydantic cannot handle Pandas `DataFrame`s, for example, or `datetime` values, so in the above code you can see that we have to convert them at various points.
{% endhint %}

For more information and a full list of configurable attributes of the Feast feature store, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-feast/#zenml.integrations.feast.feature\_stores.feast\_feature\_store.FeastFeatureStore) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
