# 🚀 Local model deployment with BentoML deployments

BentoML is an open source framework for serving, managing, and deploying machine 
learning models. It provides a high-level API for defining models and model 
servers, and supports all major machine learning frameworks, including 
Tensorflow, Keras, PyTorch, XGBoost, scikit-learn, and etc.

This example demonstrates how you can use BentoML to serve your models locally
with ZenML. While the integration offers a way to deploy your models locally,
you can also use it to deploy your models in a cloud environment, or on a
Kubernetes environment by exporting the built Bentos. 

## 🗺 Overview

The example uses the
[Fashion-MNIST](https://keras.io/api/datasets/mnist/) dataset to
train a classifier using [PyTorch](https://pytorch.org/).

In order to show how a project can use a model deployer such as BentoML, this
example contains two pipelines:

* `train_fashion_mnist` - this pipeline loads the Fashion-MNIST dataset, 
trains a classifier, and uses the built-in bento_builder and bentoml_deployer 
steps to build and deploy the model.
 
* `inference_fashion_mnist` - this pipeline loads samples of images stored 
in a folder within the repo, calls the prediction service to get the 
prediction url, and then calls the prediction url to make predictions. 

## 🧰 How the example is implemented
This example contains two very important aspects that should be highlighted.

### 🛠️ BentoML Service and runner definition

In order to use BentoML, you need to define a service and a runner. The service
is the main logic that defines how your model will be served, and the runner
represents a unit of execution for your model on a remote Python worker.

```python
import bentoml
import numpy as np
from bentoml.io import Image, NumpyNdarray

mnist_runner = bentoml.pytorch.get(MODEL_NAME).to_runner()

svc = bentoml.Service(name=SERVICE_NAME, runners=[mnist_runner])

def to_numpy(tensor):
    return tensor.detach().cpu().numpy()

@svc.api(
    input=NumpyNdarray(dtype="float32", enforce_dtype=True),
    output=NumpyNdarray(dtype="int64"),
)
async def predict_ndarray(inp: NDArray[t.Any]) -> NDArray[t.Any]:
    assert inp.shape == (28, 28)
    # We are using greyscale image and our PyTorch model expect one
    # extra channel dimension. Then we will also add one batch
    # dimension
    inp = np.expand_dims(inp, (0, 1))
    output_tensor = await mnist_runner.async_run(inp)
    return to_numpy(output_tensor)
...
```

More information about BentoML Service and runner can be found in the
[BentoML documentation](https://docs.bentoml.org/en/latest/concepts/service.html).

### ↩️ BentoML bento builder step

Once you have defined your service and runner, you can use the built-in
`bento_builder` step within your ZenML pipeline to save build a bento. This step
will save the source code, models, data files and dependency configurations 
required for running the service.

```python
from zenml.integrations.bentoml.steps import bento_builder_step

bento_builder = bento_builder_step.with_options(
    parameters=dict(
        model_name=MODEL_NAME,
        model_type="pytorch",
        service="service.py:svc",
        labels={
            "framework": "pytorch",
            "dataset": "mnist",
            "zenml_version": "0.21.1",
        },
        exclude=["data"],
        python={
            "packages": ["zenml", "torch", "torchvision"],
        },
    )
)
```

For more information about the `bento_builder` step parameters, please refer 
to the [bento builder step]()

### ↩️ BentoML Deployer step

The `bentoml_deployer` step is used to deploy the built bento to a local
environment. This step will start a local server that will serve the model
locally. 

```python
from constants import MODEL_NAME
from zenml.integrations.bentoml.steps import bentoml_model_deployer_step

bentoml_model_deployer = bentoml_model_deployer_step.with_options(
    parameters=dict(
        model_name=MODEL_NAME,  # Name of the model
        port=3001,  # Port to be used by the http server
        production=False,  # Deploy the model in production mode
    )
)
```
For more information about the `bentoml_deployer` step parameters, please refer 
to the [bentoml deployer step]()

# 🖥 Run it locally

## ⏩ SuperQuick `bentoml` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run bentoml_deployment
```

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install bentoml pytorch

# pull example
zenml example pull bentoml_deployment
cd zenml_examples/bentoml_deployment

# initialize
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```
### 🥞 Setting up the ZenML Stack

The example can only be executed with a ZenML stack that has BentoML model
deployer. Configuring a new stack could look like this:

```
zenml integration install bentoml
zenml model-deployer register bentoml_deployer --flavor=bentoml
zenml stack register local_bentoml_stack \
  -a default \
  -o default \
  -d bentoml_deployer \
  --set
```

### ▶️ Run the Code
To run the deployment pipeline:

```shell
python run.py --config deploy
```

The inference pipeline will use the currently running BentoML http deployment 
server to perform an online prediction. To run the inference pipeline:

```shell
python run.py --config predict
```

The `zenml model-deployer models list` CLI command can be run to list the 
active model servers:

```
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME          │ MODEL_NAME    ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼─────────────────────────────┼───────────────┨
┃   ✅   │ cd38d6e6-467b-46e0-be13-3112c6e65d0e │ bentoml_fashion_mnist_pipeline │ bentoml_model_deployer_step │ pytorch_mnist ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction 
URL, the `zenml model-deployer models describe <uuid>` CLI command can be run:

```
$ zenml model-deployer models describe cd38d6e6-467b-46e0-be13-3112c6e65d0e
        Properties of Served Model cd38d6e6-467b-46e0-be13-3112c6e65d0e       
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ BENTO_TAG              │ pytorch_mnist_service:kq25r5c6fgidomup                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ BENTO_URI              │ /Users/.../local_stores/c0746cb9-04c8-4273-9881-9ecf6784b051/bento_builder_────┃
┃                        │ step/output/10/zenml_exported.bento                                            ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ DAEMON_PID             │ 98699                                                                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ pytorch_mnist                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ /Users/.../local_stores/c0746cb9-04c8-4273-9881-9ecf6784b051/trainer/output/2  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ bentoml_fashion_mnist_pipeline                                                 ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RUN_NAME               │ bentoml_fashion_mnist_pipeline-2022_11_07-00_18_30_882755                      ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ bentoml_model_deployer_step                                                    ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_APIS_URLS   │ http://127.0.0.1:3001/predict_ndarray  http://127.0.0.1:3001/predict_image     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://127.0.0.1:3001/                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SERVICE_PATH           │ /Users/.../local_stores/86c7fc93-f4c0-460b-b430-7d8f5143ba88/cd38d6e6-467b-46e0┃
┃                        │ -be13-3112c6e65d0e                                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │                                                                                ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                   │ cd38d6e6-467b-46e0-be13-3112c6e65d0e                                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:

```shell
$ zenml model-deployer models get-url cd38d6e6-467b-46e0-be13-3112c6e65d0e
  Prediction URL of Served Model cd38d6e6-467b-46e0-be13-3112c6e65d0e is:
  http://localhost:3001/
```

Finally, a model server can be deleted with the 
`zenml model-deployer models delete <uuid>` CLI command:

```shell
$ zenml model-deployer models delete cd38d6e6-467b-46e0-be13-3112c6e65d0e
Model server BentoMLDeploymentService[cd38d6e6-467b-46e0-be13-3112c6e65d0e] 
(type: model-serving, flavor: bentoml) was deleted.
```

# From local to cloud with Bentoctl

Once a model server has been deployed locally, and tested, it can be deployed to
a cloud provider. This is done with the [bentoctl](https://github.com/bentoml/bentoctl) 
which is a CLI tool for managing BentoML deployments on cloud providers.

## Prerequisites

To use Bentoctl, you need : 

1. An account with a cloud provider. Currently, Bentoctl supports AWS, GCP, 
and Azure. You will also need to have the corresponding CLI tools installed 
on your machine. 
2. Docker installed on your machine.
3. Terraform installed on your machine.

## Setup Bentoctl

To install Bentoctl, run the following command:

```shell
pip install bentoctl
```

## Deploying to AWS Sagemaker with Bentoctl

In this example we will deploy the already built Bento from ZenML Pipeline
and deploy it to AWS Sagemaker.

### 1. Install AWS Sagemaker Plugin

To deploy a bento to AWS Sagemaker, we need to install the AWS Sagemaker
bentoctl plugin:

```shell
zenml integration install aws s3
bentoctl operator install aws-sagemaker
```

### 2. Initialize deployment with bentoctl

To initialize a deployment, we need to run the following command:

```shell
bentoctl init

"""
api_version: v1
name: zenml-bentoml-example
operator:
    name: aws-sagemaker
template: terraform
spec: 
    region: eu-central-1
    instance_type: ml.m5.large
    initial_instance_count: 1
    timeout: 60
    enable_data_capture: False
    destination_s3_uri: 
    initial_sampling_percentage: 1
filename for deployment_config [deployment_config.yaml]: 
deployment config generated to: deployment_config.yaml
✨ generated template files.
  - ./main.tf
  - ./bentoctl.tfvars
"""
```

### 3. Build and push AWS sagemaker compatible docker image to the registry

```shell
bentoctl build -b $BENTO_TAG -f $DEPLOYMENT_CONFIG_FILE

# Example:
bentoctl build -b pytorch_mnist_service:kq25r5c6fgidomup -f deployment_config.yaml
```

### 4. Apply Deployment Terraform and bentoctl

```shell
bentoctl apply
```

### 5. Get the endpoint

```shell
URL=$(terraform output -json | jq -r .endpoint.value)predict
```

### 🧽 Clean up

To stop any prediction servers running in the background, use the
`zenml model-server list` and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete cd38d6e6-467b-46e0-be13-3112c6e65d0e
```

To delete the Sagemaker deployment, run the following command:

```shell
bentoctl destroy
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the BentoML deployment integration can be found 
[here](https://docs.zenml.io/user-guide/component-guide/model-deployers/bentoml).

If you want to learn more about deployment in ZenML in general or about how to 
build your own deployer steps in ZenML check out our 
[docs](https://docs.zenml.io/user-guide/component-guide/model-deployers/custom).
