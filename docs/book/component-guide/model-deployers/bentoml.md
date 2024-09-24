---
description: Deploying your models locally with BentoML.
---

# BentoML

BentoML is an open-source framework for machine learning model serving. it can be used to deploy models locally, in a cloud environment, or in a Kubernetes environment.

The BentoML Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) stack component. Provided with the BentoML integration it can be used to deploy and [manage BentoML models](https://docs.bentoml.org/en/latest/guides/model-store.html#manage-models) or [Bento](https://docs.bentoml.org/en/latest/reference/stores.html#manage-bentos) on a local running HTTP server.

{% hint style="warning" %}
The BentoML Model Deployer can be used to deploy models for local development and production use cases. There are two paths to deploy Bentos with ZenML, one as a local http server and one as a containerized service. Within the BentoML ecosystem, [Yatai](https://github.com/bentoml/Yatai) and [`bentoctl`](https://github.com/bentoml/bentoctl) are the tools responsible for deploying the Bentos into the Kubernetes cluster and Cloud Platforms. `bentoctl` is deprecated now and might not work with the latest BentoML versions.
{% endhint %}

## When to use it?

You should use the BentoML Model Deployer to:

* Standardize the way you deploy your models to production within your organization.
* if you are looking to deploy your models in a simple way, while you are still able to transform your model into a production-ready solution when that time comes.

If you are looking to deploy your models with other Kubernetes-based solutions, you can take a look at one of the other [Model Deployer Flavors](./model-deployers.md#model-deployers-flavors) available in ZenML.

BentoML also allows you to deploy your models in a more complex production-grade setting. [Bentoctl](https://github.com/bentoml/bentoctl) is one of the tools that can help you get there. Bentoctl takes your built Bento from a ZenML pipeline and deploys it with `bentoctl` into a cloud environment such as AWS Lambda, AWS SageMaker, Google Cloud Functions, Google Cloud AI Platform, or Azure Functions. Read more about this in the [From Local to Cloud with `bentoctl` section](bentoml.md#from-local-to-cloud-with-bentoctl).

{% hint style="info" %}
The `bentoctl` integration implementation is still in progress and will be available soon. The integration will allow you to deploy your models to a specific cloud provider with just a few lines of code using ZenML built-in steps.
{% endhint %}

## How do you deploy it?

Within ZenML you can quickly get started with BentoML by simply creating Model Deployer Stack Component with the BentoML flavor. To do so you'll need to install the required Python packages on your local machine to be able to deploy your models:

```bash
zenml integration install bentoml -y
```

To register the BentoML model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register bentoml_deployer --flavor=bentoml
```

The ZenML integration will provision a local HTTP deployment server as a daemon process that will continue to run in the background to serve the latest models and Bentos.

## How do you use it?

The recommended flow to use the BentoML model deployer is to first [create a BentoML Service](bentoml.md#create-a-bentoml-service), then [use the `bento_builder_step`](bentoml.md#zenml-bento-builder-step) to build the model and service into a bento bundle, and finally [deploy the bundle with the `bentoml_model_deployer_step`](bentoml.md#zenml-bentoml-deployer-step).

### Create a BentoML Service

The first step to being able to deploy your models and use BentoML is to create a [bento service](https://docs.bentoml.com/en/latest/guides/services.html) which is the main logic that defines how your model will be served. The 

The following example shows how to create a basic bento service that will be used to serve a torch model. Learn more about how to specify the inputs and outputs for the APIs and how to use validators in the [Input and output types BentoML docs](https://docs.bentoml.com/en/latest/guides/iotypes.html)

```python
import bentoml
from bentoml.validators import DType, Shape
import numpy as np
import torch


@bentoml.service(
    name=SERVICE_NAME,
)
class MNISTService:
    def __init__(self):
        # load model
        self.model = bentoml.pytorch.load_model(MODEL_NAME)
        self.model.eval()

    @bentoml.api()
    async def predict_ndarray(
        self, 
        inp: Annotated[np.ndarray, DType("float32"), Shape((28, 28))]
    ) -> np.ndarray:
        inp = np.expand_dims(inp, (0, 1))
        output_tensor = await self.model(torch.tensor(inp))
        return to_numpy(output_tensor)

    @bentoml.api()
    async def predict_image(self, f: PILImage) -> np.ndarray:
        assert isinstance(f, PILImage)
        arr = np.array(f) / 255.0
        assert arr.shape == (28, 28)
        arr = np.expand_dims(arr, (0, 1)).astype("float32")
        output_tensor = await self.model(torch.tensor(arr))
        return to_numpy(output_tensor)

```

### ZenML Bento Builder step

Once you have your bento service defined, we can use the built-in bento builder step to build the bento bundle that will be used to serve the model. The following example shows how can call the built-in bento builder step within a ZenML pipeline. Make sure you have the bento service file in your repository and then use the correct class name in the `service` parameter.

```python
from zenml import pipeline, step
from zenml.integrations.bentoml.steps import bento_builder_step

@pipeline
def bento_builder_pipeline():
    model = ...
    bento = bento_builder_step(
        model=model,
        model_name="pytorch_mnist",  # Name of the model
        model_type="pytorch",  # Type of the model (pytorch, tensorflow, sklearn, xgboost..)
        service="service.py:CLASS_NAME",  # Path to the service file within zenml repo
        labels={  # Labels to be added to the bento bundle
            "framework": "pytorch",
            "dataset": "mnist",
            "zenml_version": "0.21.1",
        },
        exclude=["data"],  # Exclude files from the bento bundle
        python={
            "packages": ["zenml", "torch", "torchvision"],
        },  # Python package requirements of the model
    )
```

The Bento Builder step can be used in any orchestration pipeline that you create with ZenML. The step will build the bento bundle and save it to the used artifact store. Which can be used to serve the model in a local or containerized setting using the BentoML Model Deployer Step, or in a remote setting using the `bentoctl` or Yatai. This gives you the flexibility to package your model in a way that is ready for different deployment scenarios.

### ZenML BentoML Deployer step

We have now built our bento bundle, and we can use the built-in `bentoml_model_deployer_step` to deploy the bento bundle to our local HTTP server or to a containerized service running in your local machine. 

{% hint style="info" %}
The `bentoml_model_deployer_step` can only be used in a local environment. But in the case of using containerized deployment, you can use the Docker image created by the `bentoml_model_deployer_step` to deploy your model to a remote environment. It is automatically pushed to your ZenML Stack's container registry.
{% endhint %}

**Local deployment**

The following example shows how to use the `bentoml_model_deployer_step` to deploy the bento bundle to a local HTTP server.

```python
from zenml import pipeline, step
from zenml.integrations.bentoml.steps import bentoml_model_deployer_step

@pipeline
def bento_deployer_pipeline():
    bento = ...
    deployed_model = bentoml_model_deployer_step(
        bento=bento
        model_name="pytorch_mnist",  # Name of the model
        port=3001,  # Port to be used by the http server
    )
```

**Containerized deployment**

The following example shows how to use the `bentoml_model_deployer_step` to deploy the bento bundle to a [containerized service](https://docs.bentoml.org/en/latest/guides/containerization.html) running in your local machine. Make sure you have the `docker` CLI installed on your local machine to be able to build an image and deploy the containerized service.

You can choose to give a name and a tag to the image that will be built and pushed to your ZenML Stack's container registry. By default, the bento tag is used. If you are providing a custom image name, make sure that you attach the right registry name as prefix to the image name, otherwise the image push will fail.

```python
from zenml import pipeline, step
from zenml.integrations.bentoml.steps import bentoml_model_deployer_step

@pipeline
def bento_deployer_pipeline():
    bento = ...
    deployed_model = bentoml_model_deployer_step(
        bento=bento
        model_name="pytorch_mnist",  # Name of the model
        port=3001,  # Port to be used by the http server
        deployment_type="container",
        image="my-custom-image",
        image_tag="my-custom-image-tag",
        platform="linux/amd64",
    )
```

This step:
- builds a docker image for the bento and pushes it to the container registry
- runs the docker image locally to make it ready for inference

You can find the image on your machine by running:

```bash
docker images
```
and also the running container by running:

```bash
docker ps
```

The image is also pushed to the container registry of your ZenML stack. You can run the image in any environment with a sample command like this:

```bash
docker run -it --rm -p 3000:3000 image:image-tag serve
```

### ZenML BentoML Pipeline examples

Once all the steps have been defined, we can create a ZenML pipeline and run it. The bento builder step expects to get the trained model as an input, so we need to make sure either we have a previous step that trains the model and outputs it or loads the model from a previous run. Then the deployer step expects to get the bento bundle as an input, so we need to make sure either we have a previous step that builds the bento bundle and outputs it or load the bento bundle from a previous run or external source.

The following example shows how to create a ZenML pipeline that trains a model, builds a bento bundle, creates and runs a docker image for it and pushes it to the container registry. You can then have a different pipeline that retrieves the image and deploys it to a remote environment.

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
    deployer(deploy_decision=decision, bento=bento, deployment_type="container")

```

In more complex scenarios, you might want to build a pipeline that trains a model and builds a bento bundle in a remote environment. Then creates a new pipeline that retrieves the bento bundle and deploys it to a local http server, or to a cloud provider. The following example shows a pipeline example that does exactly that.

```python
# Import the pipeline to use the pipeline decorator
from zenml.pipelines import pipeline


# Pipeline definition
@pipeline
def remote_train_pipeline(
        importer,
        trainer,
        evaluator,
        bento_builder,
):
    """Link all the steps and artifacts together"""
    train_dataloader, test_dataloader = importer()
    model = trainer(train_dataloader)
    accuracy = evaluator(test_dataloader=test_dataloader, model=model)
    bento = bento_builder(model=model)


@pipeline
def local_deploy_pipeline(
        bento_loader,
        deployer,
):
    """Link all the steps and artifacts together"""
    bento = bento_loader()
    deployer(deploy_decision=decision, bento=bento)

```

### Predicting with the local deployed model

Once the model has been deployed we can use the BentoML client to send requests to the deployed model. ZenML will automatically create a BentoML client for you and you can use it to send requests to the deployed model by simply calling the service to predict the method and passing the input data and the API function name.

The following example shows how to use the BentoML client to send requests to the deployed model.

```python
@step
def predictor(
        inference_data: Dict[str, List],
        service: BentoMLDeploymentService,
) -> None:
    """Run an inference request against the BentoML prediction service.

    Args:
        service: The BentoML service.
        data: The data to predict.
    """

    service.start(timeout=10)  # should be a NOP if already started
    for img, data in inference_data.items():
        prediction = service.predict("predict_ndarray", np.array(data))
        result = to_labels(prediction[0])
        rich_print(f"Prediction for {img} is {result}")
```

Deploying and testing locally is a great way to get started and test your model. However, a real-world scenario will most likely require you to deploy your model to a remote environment. You can choose to deploy your model as a container image by setting the `deployment_type` to container in the deployer step and then use the image created in a remote environment. You can also use  `bentoctl` or `yatai` to deploy the bento to a cloud environment.

### From Local to Cloud with `bentoctl`

{% hint style="warning" %}
The `bentoctl` CLI is now deprecated and might not work with the latest BentoML versions.
{% endhint %}

Bentoctl helps deploy any machine learning models as production-ready API endpoints into the cloud. It is a command line tool that provides a simple interface to manage your BentoML bundles.

The `bentoctl` CLI provides a list of operators which are plugins that interact with cloud services, some of these operators are:

* [AWS Lambda](https://github.com/bentoml/aws-lambda-deploy)
* [AWS SageMaker](https://github.com/bentoml/aws-sagemaker-deploy)
* [AWS EC2](https://github.com/bentoml/aws-ec2-deploy)
* [Google Cloud Run](https://github.com/bentoml/google-cloud-run-deploy)
* [Google Compute Engine](https://github.com/bentoml/google-compute-engine-deploy)
* [Azure Container Instances](https://github.com/bentoml/azure-container-instances-deploy)
* [Heroku](https://github.com/bentoml/heroku-deploy)

To deploy your BentoML bundle to the cloud, you need to install the `bentoctl` CLI and the operator plugin for the cloud service you want to deploy to.

```bash
# Install bentoctl CLI
pip install bentoctl
# Install a choose operator
bentoctl operator install $OPERATOR # example: aws-lambda
```

Once you have the `bentoctl` CLI and the operator plugin installed, you can use the `bentoctl` CLI to deploy your BentoML bundle to the cloud.

```bash
# Let's get the name of the BentoML bundle we want to deploy
bentoml list

# Generate deployment configuration file
bentoctl init

# Build and push the Docker image to the cloud
bentoctl build -b $BENTO_TAG -f deployment_config.yaml

# Deploy to the cloud
bentoctl apply -f deployment_config.yaml
```

For more information and a full list of configurable attributes of the BentoML Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-bentoml/#zenml.integrations.bentoml.model_deployers.bentoml_model_deployer) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
