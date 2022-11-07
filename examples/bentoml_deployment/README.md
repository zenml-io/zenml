# 🚀 Local model deployment with BentoML deployments



## 🗺 Overview

The example uses the
[Fashion-MNIST](https://keras.io/api/datasets/mnist/) dataset to
train a classifier using [PyTorch](https://pytorch.org/).


## 🧰 How the example is implemented
This example contains two very important aspects that should be highlighted.

### 🛠️ BentoML Service and runner definition

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

### ↩️ BentoML bento builder step

```python
from zenml.integrations.bentoml.steps import (
    BentoMLBuilderParameters,
    bento_builder_step,
)

bento_builder = bento_builder_step(
    params=BentoMLBuilderParameters(
        model_name=MODEL_NAME,
        model_type="pytorch",
        service="service.py:svc",
        labels={
            "framework": "pytorch",
            "dataset": "mnist",
            "zenml_version": "0.21.1",
        },
       exclude=["data"], 
    )
)
```

### ↩️ BentoML Deployer step

```python
from constants import MODEL_NAME
from zenml.integrations.bentoml.steps import (
    BentoMLDeployerParameters,
    bentoml_model_deployer_step,
)

bentoml_model_deployer = bentoml_model_deployer_step(
    params=BentoMLDeployerParameters(
        model_name=MODEL_NAME,
        port=3001,
        production=False,
    )
)
```

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

The inference pipeline will use the currently running BentoML http deployment server
to perform an online prediction. To run the inference pipeline:

```shell
python run.py --config predict
```

The `zenml model-deployer models list` CLI command can be run to list the active model servers:

```
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME          │ MODEL_NAME    ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼─────────────────────────────┼───────────────┨
┃   ✅   │ cd38d6e6-467b-46e0-be13-3112c6e65d0e │ bentoml_fashion_mnist_pipeline │ bentoml_model_deployer_step │ pytorch_mnist ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml model-deployer models describe <uuid>` CLI command can be run:

```
$ zenml model-deployer models describe cd38d6e6-467b-46e0-be13-3112c6e65d0e
        Properties of Served Model cd38d6e6-467b-46e0-be13-3112c6e65d0e       
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ BENTO_TAG              │ pytorch_mnist_service:kq25r5c6fgidomup                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ BENTO_URI              │ /Users/.../local_stores/c0746cb9-04c8-4273-9881-9ecf6784b051/bento_builder_ ┃
┃                        │ step/output/10/zenml_exported.bento                                            ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ DAEMON_PID             │ 98699                                                                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ pytorch_mnist                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ /Users/.../local_stores/c0746cb9-04c8-4273-9881-9ecf6784b051/trainer/output ┃
┃                        │ /2                                                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ bentoml_fashion_mnist_pipeline                                                 ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_RUN_ID        │ bentoml_fashion_mnist_pipeline-2022_11_07-00_18_30_882755                      ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ bentoml_model_deployer_step                                                    ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICITON_APIS_URLS   │ http://127.0.0.1:3001/predict_ndarray  http://127.0.0.1:3001/predict_image     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://127.0.0.1:3001/                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SERVICE_PATH           │ /Users/.../local_stores/86c7fc93-f4c0-460b-b430-7d8f5143ba88/cd38d6e6-467b- ┃
┃                        │ 46e0-be13-3112c6e65d0e                                                         ┃
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

Finally, a model server can be deleted with the `zenml model-deployer models delete <uuid>`
CLI command:

```shell
$ zenml model-deployer models delete cd38d6e6-467b-46e0-be13-3112c6e65d0e
Model server BentoMLDeploymentService[cd38d6e6-467b-46e0-be13-3112c6e65d0e] 
(type: model-serving, flavor: bentoml) was deleted.
```

### 🧽 Clean up

To stop any prediction servers running in the background, use the
`zenml model-server list` and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete cd38d6e6-467b-46e0-be13-3112c6e65d0e
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the BentoML deployment integration can be found [here](https://docs.zenml.io/component-gallery/model-deployers/bentoml).

If you want to learn more about deployment in ZenML in general or about how to 
build your own deployer steps in ZenML check out our 
[docs](https://docs.zenml.io/component-gallery/model-deployers/custom).
