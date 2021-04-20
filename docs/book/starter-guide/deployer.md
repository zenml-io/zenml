# Deploy your model

## Overview

In order to deploy a trained model, ZenML uses an interface called the `BaseDeployer`. 

{% hint style="danger" %}
As of **0.3.6**, the mechanism to create custom deployers is not supported. We are working hard to bring you this feature and if you would like to learn more about our progress you can check our [roadmap](../support/roadmap.md).  Meanwhile, you can use our built-in **CortexDeployer** or **GCAIPDeployer**.
{% endhint %}

## Example: the built-in `CortexDeployer`

The `CortexDeployer` is built to make it easier to deploy models on a Kubernetes cluster and for this purpose, it utilizes the [Cortex integration of **ZenML**](../advanced-guide/integrations.md).

{% code title="zenml/examples/cortex/run.py" %}
```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.deployer import CortexDeployer

training_pipeline = TrainingPipeline()

...

api_config = {
    "name": CORTEX_MODEL_NAME,
    "kind": "RealtimeAPI",
    "predictor": {
        "type": "tensorflow",
        "models": {"signature_key": "serving_default"}}}
        
training_pipeline.add_deployment(
    CortexDeployer(
        env=CORTEX_ENV,
        api_config=api_config,
        predictor=TensorFlowPredictor))
        
...
```
{% endcode %}

In order to get a better understanding of how the `CortexDeployer` works, you can check our full example right [here](https://github.com/maiot-io/zenml/blob/main/examples/cortex/run.py).

## Example: the built-in `GCAIPDeployer`

With **ZenML**, you can deploy a trained model on the Google Cloud AI Platform using the `GCAIPDeployer`. The usage of the `GCAIPDeployer` is limited to Tensorflow-based trainers and you need to install the [GCP integration of **ZenML**](../advanced-guide/integrations.md).

{% code title="zenml/examples/gcp\_gcaip\_deployment/run.py" %}
```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.deployer import GCAIPDeployer

training_pipeline = TrainingPipeline()

...

training_pipeline.add_deployment(
    GCAIPDeployer(
        project_id=GCP_PROJECT,
        model_name=MODEL_NAME,
    )
)

...
```
{% endcode %}

If you would like to see how the `GCAIPDeployer` works in a full example, you can take a look at our tutorial right [here](https://github.com/maiot-io/zenml/tree/main/examples/gcp_gcaip_deployment).

