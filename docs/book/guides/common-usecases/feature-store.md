---
description:
  ZenML integrates with Feast so you can access your batch and online data via a
  Feature Store
---

Feature stores allow data teams to serve data via an offline store and an online low-latency store where data is kept in sync between the two. It also offers a centralized registry where features (and feature schemas) are stored for use within a team or wider organization.

As a data scientist working on training your model, your requirements for how you access your batch / 'offline' data will almost certainly be different from how you access that data as part of a real-time or online inference setting. Feast solves the problem of developing [train-serve skew](https://ploomber.io/blog/train-serve-skew/) where those two sources of data diverge from each other.

Feature stores are a relatively recent addition to commonly-used machine learning stacks. [Feast](https://feast.dev/) is a leading open-source feature store, first developed by [Gojek](https://www.gojek.com/en-id/) in collaboration with Google.

## 🗺 Features Stores & ZenML

There are two core functions that feature stores enable: access to data from an offline / batch store for training and access to online data at inference time. The ZenML Feast integration enables both of these behaviors.

ZenML assumes that users of the integration already have a feature store that they just need to connect with. The ZenML Feast integration currently supports your choice of offline data sources, and a [Redis](https://redis.com/) backend for your online feature serving. We encourage users to check out [Feast's documentation](https://docs.feast.dev/) and [guides](https://docs.feast.dev/how-to-guides/) on how to setup your offline and online data sources via the configuration `yaml` file.

Online data retrieval is currently possible in a local setting, but we don't currently support using the online data serving in the context of a deployed model or as part of model deployment. We will update this documentation as we develop out this feature.

# Get your offline / batch data from a Feature Store

ZenML supports access to your feature store via a stack component that you can configure via the CLI tool. (See [here](https://apidocs.zenml.io/latest/cli/) for details on how to do that.)

Getting features from a registered and active feature store is possible by creating your own step that interfaces into the feature store:

```python
entity_dict = {…} # defined in earlier code
features = […] # defined in earlier code

class FeastHistoricalFeaturesConfig(BaseStepConfig):
    """Feast Feature Store historical data step configuration."""

    entity_dict: Union[Dict[str, Any], str]
    features: List[str]
    full_feature_names: bool = False

    class Config:
        arbitrary_types_allowed = True


@step
def get_historical_features(
    config: FeastHistoricalFeaturesConfig,
    context: StepContext,
) -> pd.DataFrame:
    """Feast Feature Store historical data step

    Args:
        config: The step configuration.
        context: The step context.

    Returns:
        The historical features as a DataFrame.
    """
    if not context.stack:
        raise DoesNotExistException(
            "No active stack is available. Please make sure that you have registered and set a stack."
        )
    elif not context.stack.feature_store:
        raise DoesNotExistException(
            "The Feast feature store component is not available. "
            "Please make sure that the Feast stack component is registered as part of your current active stack."
        )

    feature_store_component = context.stack.feature_store
    config.entity_dict["event_timestamp"] = [
        datetime.fromisoformat(val)
        for val in config.entity_dict["event_timestamp"]
    ]
    entity_df = pd.DataFrame.from_dict(config.entity_dict)

    return feature_store_component.get_historical_features(
        entity_df=entity_df,
        features=config.features,
        full_feature_names=config.full_feature_names,
    )


historical_features = get_historical_features(
    config=FeastHistoricalFeaturesConfig(
        entity_dict=historical_entity_dict, features=features
    ),
)
```

Note that ZenML's use of Pydantic to serialize and deserialize inputs stored in the ZenML metadata means that we are limited to basic data types. Pydantic cannot handle Pandas `DataFrame`s, for example, or `datetime` values, so in the above code you can see that we have to convert them at various points.

# Get your online data from a Feature Store at inference time

COMING SOON: While the ZenML integration has an interface to access online feature store data, it currently is not usable in production settings with deployed models. We will update the docs when we enable this functionality.