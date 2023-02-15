# 🛤️ Manage Model Versions with MLflow Model Registry

[MLflow](https://www.mlflow.org/docs/latest/tracking.html) is a popular
tool that helps you track experiments, manage models and even deploy them to
different environments. ZenML already provides a [MLflow Experiment Tracker]()
that you can use to track your experiments, and an [MLFlow Model Deployer]() that
you can use to deploy your models locally. In this example, we will see the newest
addition to the MLflow integration, the [MLflow Model Registry](). This component
allows you to manage and track your model versions, and enables you to deploy
them to different environments with ease.

## 🗺 Overview

This example showcases how easily MLFlow Model Registry can be integrated into
your ZenML pipelines and how you can use it to manage your model versions.

We'll be using the
[MNIST-digits](https://keras.io/api/datasets/mnist/) dataset and
will train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/).
We will run three experiments with different parameters (epochs and learning rate)
and log these experiments and the models into a local mlflow backend.

This example uses an mlflow setup that is based on the local filesystem for
things like the artifact store. See the [mlflow
documentation](https://www.mlflow.org/docs/latest/tracking.html#scenario-1-mlflow-on-localhost) 
for details.

In the example script the [mlflow autologger for
Keras](https://www.mlflow.org/docs/latest/tracking.html#tensorflow-and-keras) is
used within the training step to directly hook into the TensorFlow training, and
it will log out all relevant parameters, metrics and output files. Additionally,
we explicitly log the test accuracy within the evaluation step.

This example uses an mlflow setup that is based on the local filesystem as
orchestrator and artifact store. See the [mlflow
documentation](https://www.mlflow.org/docs/latest/tracking.html#scenario-1-mlflow-on-localhost)
for details.

The example consists of two individual pipelines:

1. `train_pipeline`: Trains a model with different parameters and logs the
   results to mlflow and finishes by registering the model with the mlflow model
    registry using a built-in ZenML step.
2. `deploy_inference_pipeline`: Deploys a model from the mlflow model registry to a local
    mlflow server using a built-in ZenML step that takes the model name and
    version as input. Then it runs inference on the deployed model.

## 🧰 How the example is implemented
This example contains two very important aspects that should be highlighted.

### 🛠️ Model Version Registration within a ZenML pipeline 

ZenML provides a built-in step that allows you to register your model with the
MLflow Model Registry. This step is called `mlflow_model_register_step` and can
be used as follows:

Define a pipeline with a `mlflow_model_register_step`:

 ```python
@pipeline(enable_cache=False, settings={"docker": docker_settings})
def mlflow_training_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
    model_register,
):
    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer()
    x_trained_normed, x_test_normed = normalizer(
        x_train=x_train, x_test=x_test
    )
    model = trainer(x_train=x_trained_normed, y_train=y_train)
    evaluator(x_test=x_test_normed, y_test=y_test, model=model)
    model_register(model)
```

When referencing the step in the pipeline, you can pass list of parameters that
will be passed to the `mlflow_model_register_step` that will be used to register
the model with the MLflow Model Registry. By default, the step can extract some
of the parameters from the pipeline context, but you can also pass them
explicitly. The following code shows an example of how you can use the step:

```python
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    MLFlowDeployerParameters,
    mlflow_model_registry_deployer_step,
)

mlflow_training_pipeline(
    importer=loader_mnist(),
    normalizer=normalizer(),
    trainer=tf_trainer(params=TrainerParameters(epochs=5, lr=0.003)),
    evaluator=tf_evaluator(),
    model_register=mlflow_register_model_step(
        params=MLFlowRegistryParameters(
            name="Tensorflow-mnist-model",
            description="A simple mnist model trained with zenml",
            tags={"framework": "tensorflow", "dataset": "mnist"},
            version_tags={"lr": 0.003},
            version_description=f"The 1st run of the mlflow_training_pipeline.",
        )
    ),
).run()

# The list of parameters that can be passed to the mlflow_model_register_step:
"""
    name: Name of the registered model.
    description: Description of the registered model.
    tags: Tags to be added to the registered model.
    experiment_name: Name of the MLFlow experiment to be used for the run.
    run_name: Name of the MLFlow run to be created.
    run_id: ID of the MLFlow run to be used.
    model_source_uri: URI of the model source. If not provided, the model
        will be fetched from the MLflow tracking server.
    version_description: Description of the model.
    version_tags: Tags to be added to the model.
"""
```

### 🚀 Deploying a model from the Model Registry to a local MLflow server

Once you have registered your model with the MLflow Model Registry, you can
deploy it to a local MLflow server using the `mlflow_model_registry_deployer_step` step.

```python

from zenml.integrations.mlflow.steps.mlflow_deployer import (
    MLFlowDeployerParameters,
    mlflow_model_registry_deployer_step,
)

deployment_inference_pipeline(
    mlflow_model_deployer=mlflow_model_registry_deployer_step(
        params=MLFlowDeployerParameters(
            registry_model_name="Tensorflow-mnist-model",
            registry_model_version="1",
            # or you can use the model stage if you have set it in the mlflow registry
            # registered_model_stage="Staging",
        )
    ),
    dynamic_importer=dynamic_importer(),
    predict_preprocessor=tf_predict_preprocessor(),
    predictor=predictor(),
).run()
```
# 🖥 Run it locally

## ⏩ SuperQuick `mlflow_registry` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run mlflow_registry
```

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install mlflow tensorflow

# pull example
zenml example pull mlflow_registry
cd zenml_examples/mlflow_registry

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up

# Create and activate the stack with the mlflow model registry, tracker and deployer stack components.
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml model-registry register mlflow_registry --flavor=mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow
zenml stack register mlflow_stack \
    -a default \
    -o default \
    -e mlflow_tracker \
    -r mlflow_registry \
    -d mlflow_deployer \
    --set
```

### ▶️ Run the Code
Now we're ready. Execute:

```bash
python run.py
```

Alternatively, if you want to run based on the `config.yaml` you can run with:

```bash
# For Training pipeline Use:
zenml pipeline run pipelines/training_pipeline/training_pipeline.py -c training_pipeline_config.yaml
# For Deployment pipeline Use:
zenml pipeline run pipelines/deployment_inference_pipeline/deployment_inference_pipeline.py -c deployment_pipeline_config.yaml
```

## Running on a local Kubernetes cluster


## 📄 Infrastructure Requirements (Pre-requisites)

You don't need to set up any infrastructure to run your pipelines with MLflow on a Kubernetes cluster, locally. However, you need the following tools installed:
  * Docker must be installed on your local machine.
  * Install k3d by running `curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash`.

## Create a local MLflow Stack

To get a stack with MLflow installed with authentication and potential other components, you can make use of ZenML's Stack Recipes that are a set of terraform based modules that take care of setting up a cluster with MLflow among other things.

Run the following command to deploy the local MLflow stack:

```bash
zenml stack recipe deploy k3d-modular
```

>**Note**:
> This recipe comes with MLflow, Kubeflow and Minio enabled by default. If you want any other components like KServe, Seldon or Tekton, you can specify that using the `--install/-i` flag.

This will deploy a local Kubernetes cluster with MLflow installed. 
It will also generate a stack YAML file that you can import as a ZenML stack by running 

```bash
zenml stack import -f <path-to-stack-yaml>
```
Once the stack is set, you can then simply proceed to running your pipelines.

### 🔮 See results
Now we just need to start the mlflow UI to have a look at our two pipeline runs.
To do this we need to run:

```shell
mlflow ui --backend-store-uri <SPECIFIC_MLRUNS_PATH_GOES_HERE>
```

Check the terminal output of the pipeline run to see the exact path appropriate
in your specific case. This will start mlflow at `localhost:5000`. If this port
is already in use on your machine you may have to specify another port:

```shell
 mlflow ui --backend-store-uri <SPECIFIC_MLRUNS_PATH_GOES_HERE> -p 5001
 ```

### 🧽 Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
rm -rf <SPECIFIC_MLRUNS_PATH_GOES_HERE>
```

# 📜 Learn more

Our docs regarding the MLflow model registry integration can be found 
[here](https://docs.zenml.io/component-gallery/model-registries/mlflow).


If you want to learn more about model registries in general or about how to 
build your own model registry in ZenML check out our 
[docs](https://docs.zenml.io/component-gallery/model-registries/custom).
