---
description: Managing data in Feast feature stores.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Feast

Feast (Feature Store) is an operational data system for managing and serving machine learning features to models in
production. Feast is able to serve feature data to models from a low-latency online store (for real-time prediction) or
from an offline store (for scale-out batch scoring or model training).

### When would you want to use it?

There are two core functions that feature stores enable:

* access to data from an offline / batch store for training.
* access to online data at inference time.

Feast integration currently supports your choice of offline data sources and a [Redis](https://redis.com/) backend for
your online feature serving. We encourage users to check out [Feast's documentation](https://docs.feast.dev/)
and [guides](https://docs.feast.dev/how-to-guides/) on how to set up your offline and online data sources via the
configuration `yaml` file.

{% hint style="info" %}
COMING SOON: While the ZenML integration has an interface to access online feature store data, it currently is not
usable in production settings with deployed models. We will update the docs when we enable this functionality.
{% endhint %}

### How to deploy it?

The Feast Feature Store flavor is provided by the Feast ZenML integration, you need to install it, to be able to
register it as a Feature Store and add it to your stack:

```shell
zenml integration install feast
```

Since this example is built around a Redis use case, a Python package to interact with Redis will get installed
alongside Feast, but you will still first need to install Redis yourself. See this page for some instructions on how to
do that on your operating system.

You will then need to run a Redis server in the background in order for this example to work. You can either use the
Redis-server command in your terminal (which will run a continuous process until you CTRL-C out of it), or you can run
the daemonized version:

```shell
redis-server --daemonize yes

# verify it is running (Unix machines)
ps aux | grep redis-server
```

### How do you use it?

ZenML assumes that users already have a feature store that they just need to connect with. The ZenML Online data
retrieval is currently possible in a local setting, but we don't currently support using the online data serving in the
context of a deployed model or as part of model deployment. We will update this documentation as we develop this
feature.

ZenML supports access to your feature store via a stack component that you can configure via the CLI tool. (
See [here](https://sdkdocs.zenml.io/latest/cli/) for details on how to do that.)

Getting features from a registered and active feature store is possible by creating your own step that interfaces into
the feature store:

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
```

{% hint style="warning" %}
Note that ZenML's use of Pydantic to serialize and deserialize inputs stored in the ZenML metadata means that we are
limited to basic data types. Pydantic cannot handle Pandas `DataFrame`s, for example, or `datetime` values, so in the
above code you can see that we have to convert them at various points.
{% endhint %}

A concrete example of using the Feast feature store can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/feast\_feature\_store).

For more information and a full list of configurable attributes of the Feast feature store, check out
the [API Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-feast/#zenml.integrations.feast.feature\_stores.feast\_feature\_store.FeastFeatureStore)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
