---
description: Build and deploy ML models using Baseten.
---

# Baseten

Baseten is a platform for building and deploying machine learning models. It uses [Truss](https://truss.baseten.co/), an open-source tool for packaging models into deployable units.

The Baseten Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) stack component. Provided with the Baseten integration, it can be used to deploy and manage [Truss](https://truss.baseten.co/) models on the Baseten platform.

## When to use it?

You should use the Baseten Model Deployer:

*   If you want to deploy your models using the Baseten platform.
*   If you are looking for a serverless solution for your ML models without dealing with the complexity of infrastructure management, while still having access to GPUs.
*   If you need to package your models using Truss for easy deployment to Baseten.

If you are looking to deploy your models with other Kubernetes-based solutions, or more simple local solutions, you can take a look at one of the other [Model Deployer Flavors](./model-deployers.md#model-deployers-flavors) available in ZenML.

## How to deploy it?

The Baseten Model Deployer flavor is provided by the Baseten ZenML integration, so you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install baseten -y
```

To register the Baseten model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register baseten_deployer --flavor=baseten --baseten_api_key={{baseten_secret.api_key}}
```

{% hint style="info" %}
We recommend creating a Baseten API key with the necessary permissions to create and run deployments. You can find more information on how to create an API key in the [Baseten documentation](https://docs.baseten.co/reference/api-keys/). You will need to create a ZenML secret to store the Baseten API key, and then use it to register the Baseten Model Deployer. See the [Storing the Baseten API key in a ZenML Secret](#storing-the-baseten-api-key-in-a-zenml-secret) section for more information.
{% endhint %}

The ZenML integration will package your model and deploy it to the Baseten platform using Truss.

### Storing the Baseten API key in a ZenML Secret

You can create a secret, for example named `baseten_secret`, that includes a key `api_key`. This can be done via CLI or the Python SDK.

```bash
zenml secret create baseten_secret --api_key=<YOUR_BASETEN_API_KEY_VALUE>
```

(or using the Python client):

```python
from zenml.client import Client

Client().create_secret(
    name="baseten_secret",
    values={"api_key": "YOUR_BASETEN_API_KEY_VALUE"}
)
```

This keeps your Baseten credentials out of code and in the ZenML secrets store.

## How do you use it?

The recommended flow to use the Baseten model deployer is to first [create a Truss](#create-a-truss-directory), then [deploy the Truss with the `baseten_model_deployer_step`](#zenml-baseten-deployer-step).

### Create a Truss directory

A Truss is a directory containing your model code, dependencies, and configuration. The Baseten model deployer expects a directory which contains a `config.yaml` file and a `model.py` file. You can create a truss directory with the following python code:

```python
import os
import joblib
from sklearn.ensemble import RandomForestClassifier

def create_truss(
    model: RandomForestClassifier,
    truss_dir: str = "iris_truss",
) -> str:
    """Create a Truss directory for the model.

    Args:
        model: The trained model.
        truss_dir: The directory to create the Truss in.

    Returns:
        The path to the Truss directory.
    """
    # Create the Truss directory if it doesn't exist
    os.makedirs(truss_dir, exist_ok=True)

    # Save the model
    model_path = os.path.join(truss_dir, "model.joblib")
    joblib.dump(model, model_path)

    # Create a basic model.py
    model_py = """
import joblib
import numpy as np

class Model:
    def __init__(self, **kwargs):
        self.model = None
        
    def load(self):
        self.model = joblib.load('model.joblib')
        
    def predict(self, request):
        instances = request["instances"]
        predictions = self.model.predict(instances)
        return {"predictions": predictions.tolist()}
"""

    with open(os.path.join(truss_dir, "model.py"), "w") as f:
        f.write(model_py)

    # Create a basic config.yaml
    config_yaml = """
model_name: iris_classifier
python_version: "py39"
requirements:
  - scikit-learn
  - joblib
model_type: custom
"""

    with open(os.path.join(truss_dir, "config.yaml"), "w") as f:
        f.write(config_yaml)

    return os.path.abspath(truss_dir)
```

### ZenML Baseten Deployer step

Once you have your Truss directory, we can use the built-in `baseten_model_deployer_step` to deploy the Truss to your Baseten account. The following example shows how can call the built-in deployer step within a ZenML pipeline. Make sure you have the Truss directory in your repository and then use the correct path to it in the `truss_dir` parameter.

```python
from zenml import pipeline, step
from zenml.integrations.baseten.steps import baseten_model_deployer_step

@pipeline
def baseten_deployer_pipeline():
    truss_dir = ...
    deployed_model = baseten_model_deployer_step(
        truss_dir=truss_dir,
        model_name="iris_classifier",  # Name of the model in Baseten
    )
```

You can use the `baseten_model_deployer_step` to deploy the bento bundle in any orchestration pipeline that you create with ZenML. The step will push the truss to Baseten and register a service that can be used to track and manage your model.

### Predicting with the deployed model

Once the model has been deployed we can use the Baseten client or directly call the API using the prediction url to send requests to the deployed model. ZenML will automatically create a Baseten client for you and you can use it to send requests to the deployed model by simply calling the service to predict the method and passing the input data.

The following example shows how to use the Baseten client to send requests to the deployed model.

```python
from typing import Any, Dict
import numpy as np
from zenml import step
from zenml.integrations.baseten.services import BasetenDeploymentService


@step
def predictor(
    service: BasetenDeploymentService,
    data: np.ndarray
) -> Dict[str, Any]:
    """Run an inference request against the Baseten prediction service.

    Args:
        service: The Baseten service.
        data: The data to predict.
    """

    response = service.predict({"instances": data.tolist()})
    return response
```

Deploying and testing locally is a great way to get started and test your model. However, a real-world scenario will most likely require you to deploy your model to a remote environment. With Baseten, you are already deploying your model to a remote serverless environment, and you can use the API endpoint to integrate with your application.

For more information and a full list of configurable attributes of the Baseten
Model Deployer, check out the [SDK
Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-baseten/#zenml.integrations.baseten.model_deployers.baseten_model_deployer).
