---
description: How to annotate data using Label Studio with ZenML
---

Label Studio is one of the leading open-source annotation platforms available to
data scientists and ML practitioners. It is used to create or edit datasets that
you can then use as part of training or validation workflows. It supports a
broad range of annotation types, including:

- Computer Vision (image classification, object detection, semantic
  segmentation)
- Audio & Speech (classification, speaker diarization, emotion recognition,
  audio transcription)
- Text / NLP (classification, NER, question answering, sentiment analysis)
- Time Series (classification, segmentation, event recognition)
- Multi Modal / Domain (dialogue processing, OCR, time series with reference)

## When would you want to use it?

If you need to label data as part of your ML workflow, that is the point at
which you could consider adding in the optional annotator stack component as
part of your ZenML stack.

We currently support the use of annotation at the various stages described in
[the main annotators docs page](./annotators.md), and also offer custom utility
functions to generate Label Studio label config files for image classification
and object detection. (More will follow in due course.)

The Label Studio integration currently is built to support workflows using cloud
artifact stores (i.e. AWS S3, GCP/GCS and Azure Blob Storage). Purely local
stacks will currently *not* work if you want to do add the annotation stack
component as part of your stack.


Feast integration currently supports your choice of offline data sources, and a
[Redis](https://redis.com/) backend for your online feature serving. We
encourage users to check out [Feast's documentation](https://docs.feast.dev/)
and [guides](https://docs.feast.dev/how-to-guides/) on how to set up your
offline and online data sources via the configuration `yaml` file.

{% hint style="info" %} COMING SOON: The Label Studio Integration supports the
use of annotations in an ML workflow, but we do not currently handle the
universal conversion between data formats as part of the training workflow. Our
initial use case was built to support image classification and object detection,
but we will add helper steps and functions for other use cases in due course. We
will update the docs when we enable this functionality. {% endhint %}

## How to deploy it?

The Label Studio Annotator flavor is provided by the Label Studio ZenML
integration, you need to install it, to be able to register it as an Annotator
and add it to your stack:

```shell
zenml integration install label_studio
```

Before registering a `label_studio` flavor stack component as part of your
stack, you'll need to have registered a cloud artifact store and a secrets
manager to handle authentication with Label Studio as well as any secrets
required for the Artifact Store. (See the docs on how to register and [setup a
cloud artifact store](../artifact-stores/artifact-stores.md) as well as [a
secrets manager](../secrets-managers/secrets-managers.md).)

You will next need to obtain your Label Studio API key. This will give you
access to the web annotation interface.

```shell
# choose a username and password for your label-studio account
label-studio reset_password --username <username> --password <password>
# start a temporary / one-off label-studio instance to get your API key
label-studio start -p 8094
```

Then visit [http://localhost:8094/](http://localhost:8094/) to log in, and then
visit [http://localhost:8094/user/account](http://localhost:8094/user/account)
and get your Label Studio API key (from the upper right hand corner). You will
need it for the next step. `Ctrl-c` out of the Label Studio server that is
running on the terminal.

At this point you should register the API key with your secrets manager under a
custom secret name, making sure to replace the two parts in `<>` with whatever
you choose:

```shell
zenml secret register <label_studio_secret_name> --api_key="<your_label_studio_api_key>"
```

Then register your annotator with ZenML:

```shell
zenml annotator register label_studio --flavor label_studio --authentication_secret="<label_studio_secret_name>"
```

Now if you run a simple CLI command like `zenml annotator dataset list` this
should work without any errors. You're ready to use your annotator in your ML workflow!

## How do you use it?

ZenML assumes that users already have a feature store that they just need to
connect with. The ZenML Online data retrieval is currently possible in a local
setting, but we don't currently support using the online data serving in the
context of a deployed model or as part of model deployment. We will update this
documentation as we develop out this feature.

ZenML supports access to your feature store via a stack component that you can
configure via the CLI tool. ( See [here](https://apidocs.zenml.io/latest/cli/)
for details on how to do that.)

Getting features from a registered and active feature store is possible by
creating your own step that interfaces into the feature store:

```python
from datetime import datetime
from typing import Any, Dict, List, Union
import pandas as pd

from zenml.steps import BaseStepConfig, step, StepContext
entity_dict = {…}  # defined in earlier code
features = […]  # defined in earlier code

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

{% hint style="warning" %} Note that ZenML's use of Pydantic to serialize and
deserialize inputs stored in the ZenML metadata means that we are limited to
basic data types. Pydantic cannot handle Pandas `DataFrame`s, for example, or
`datetime` values, so in the above code you can see that we have to convert them
at various points. {% endhint %}

A concrete example of using the Feast feature store can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/feast_feature_store).

For more information and a full list of configurable attributes of the Kubeflow
orchestrator, check out the [API
Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.feast.feature_stores.feast_feature_store.FeastFeatureStore).
