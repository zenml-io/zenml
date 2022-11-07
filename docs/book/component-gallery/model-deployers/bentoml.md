---
description: How to deploy your models locally with BentoML
---

The BentoML Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) 
stack component. Provided with the BentoML integration it can be used to deploy
and manage [BentoML models](https://docs.bentoml.org/en/latest/concepts/model.html) or 
[Bento](https://docs.bentoml.org/en/latest/concepts/bento.html)
on a local running http server.

{% hint style="warning" %}
The BentoML Model Deployer is mainly for local and development usage, 
while the integration mainly work in local environment the used 
[Bento](https://docs.bentoml.org/en/latest/concepts/bento.html) can be exported
and containerized and be deployed in a remote environment.
Within BentoML ecosystem [Yatai](https://github.com/bentoml/Yatai) and 
[bentoctl](https://github.com/bentoml/bentoctl) are the tools responsible for 
deploying the Bentos into Kubernetes cluster and Cloud Platforms a full support 
for this advanced tools is in progress and will be available soon. 
{% endhint %}

## When to use it?

BentoML is an open source framework for machine learning model serving. 
it can be used to serve to deploy models locally, in a cloud environment, or
on a Kubernetes environment.

You should use the MLflow Model Deployer:

* Standarize the way you deploy your models to production withing your organization.

* if you are looking to deploy your models in a simple way, while you are still
able to transform your model into a production ready solution when that time comes.

If you are looking to deploy your models in a more complex producation grade 
dedicated ways, you can take a look to one of the other 
[Model Deployer Flavors](./model-deployers.md#model-deployers-flavors) 
available in ZenML (e.g. Seldon Core, KServe, etc.)

## How do you deploy it?

The BentoML Model Deployer flavor is provided by the BentoML ZenML integration, 
you need to install it on your local machine to be able to deploy your models. 
You can do this by running the following command:

```bash
zenml integration install bentoml -y
```

To register the BentoML model deployer with ZenML you need to run the following
command:

```bash
zenml model-deployer register bentoml_deployer --flavor=bentoml
```

The ZenML integration will provision a local http deployment server as a 
daemon process that will continue to run in the background to serve the 
latest models and Bentos.

## How do you use it?

The first step to be able to deploy your models and use your BentoML is to create 
a [bento service](https://docs.bentoml.org/en/latest/concepts/service.html)
which is the main logic that defines how your model will be served, and
a [bento runner](https://docs.bentoml.org/en/latest/concepts/runner.html)
which represents a unit of execution for your model on a remote Python worker.

The following example shows how to create a simple bento service and runner
that will be used to serve a simple scikit-learn model.

```python
import numpy as np
import bentoml
from bentoml.io import NumpyNdarray

iris_clf_runner = bentoml.sklearn.get("iris_clf:latest").to_runner()

svc = bentoml.Service("iris_classifier", runners=[iris_clf_runner])

@svc.api(input=NumpyNdarray(), output=NumpyNdarray())
def classify(input_series: np.ndarray) -> np.ndarray:
    result = iris_clf_runner.predict.run(input_series)
    return result

```

Once you have your bento service and runner defined, we can use the
built-in bento builder step to build the bento bundle that will be used
to serve the model. The following example shows how can call the built-in
bento builder step within a ZenML pipeline.

```python
# Import the step and parameters class
from zenml.integrations.bentoml.steps import BentoMLBuilderParameters, bento_builder_step,

# The name we gave to our deployed model
MODEL_NAME = "pytorch_mnist"

# Call the step with the parameters
bento_builder = bento_builder_step(
    params=BentoMLBuilderParameters(
        model_name=MODEL_NAME,          # Name of the model
        model_type="pytorch",           # Type of the model (pytorch, tensorflow, sklearn, xgboost..)
        service="service.py:svc",       # Path to the service file within zenml repo
        labels={                        # Labels to be added to the bento bundle
            "framework": "pytorch",
            "dataset": "mnist",
            "zenml_version": "0.21.1",
        },
       exclude=["data"],                # Exclude files from the bento bundle
    )
)
```

We have now built our bento bundle, and we can use the built-in bento deployer
step to deploy the bento bundle to our local http server. The following example
shows how to call the built-in bento deployer step within a ZenML pipeline.

```python
# Import the step and parameters classe
from zenml.integrations.bentoml.steps import BentoMLDeployerParameters, bentoml_model_deployer_step,

# The name we gave to our deployed model
MODEL_NAME = "pytorch_mnist"

# Call the step with the parameters
bentoml_model_deployer = bentoml_model_deployer_step(
    params=BentoMLDeployerParameters(
        model_name=MODEL_NAME,          # Name of the model
        port=3001,                      # Port to be used by the http server
        production=False,               # Deploy the model in production mode
    )
)
```

Once all the steps have been defined, we can create a ZenML pipeline and run it.
The bento builder step expects to get the trained model as an input, so we need
to make sure either we have a previous step that trains the model and outputs it
or load the model from a previous run. Then the deployer step expects to get the
bento bundle as an input, so we need to make sure either we have a previous step
that builds the bento bundle and outputs it or load the bento bundle from a previous
run or external source.

```python
# Import the pipeline to use the pipeline decorator
from zenml.pipelines import pipeline

# Pipeline definition
@pipeline
def bentoml_pipeline(
    importer,
    trainer,
    evaluator,
    deployment_trigger,
    bento_builder,
    deployer,
):
    """Link all the steps and artifacts together"""
    train_dataloader, test_dataloader = importer()
    model = trainer(train_dataloader)
    accuracy = evaluator(test_dataloader=test_dataloader, model=model)
    decision = deployment_trigger(accuracy=accuracy)
    bento = bento_builder(model=model)
    deployer(deploy_decision=decision, bento=bento)

```

You can check the BentoML deployment example for more details.

- [Model Deployer with BentoML](https://github.com/zenml-io/zenml/tree/main/examples/bentoml_deployment)

For more information and a full list of configurable attributes of the BentoML 
Model Deployer, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-bentoml/#zenml.integrations.bentoml).