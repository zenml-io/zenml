---
icon: rocket
description: Deploying your models and serve real-time predictions.
---

# Model Deployers

Model Deployment is the process of making a machine learning model available to make predictions and decisions on
real-world data. Getting predictions from trained models can be done in different ways depending on the use case, a
batch prediction is used to generate predictions for a large amount of data at once, while a real-time prediction is
used to generate predictions for a single data point at a time.

Model deployers are stack components responsible for serving models on a real-time or batch basis.

Online serving is the process of hosting and loading machine-learning models as part of a managed web service and
providing access to the models through an API endpoint like HTTP or GRPC. Once deployed, model inference can be
triggered at any time, and you can send inference requests to the model through the web service's API and receive fast,
low-latency responses.

Batch inference or offline inference is the process of making a machine learning model make predictions on a batch of
observations. This is useful for generating predictions for a large amount of data at once. The predictions are usually
stored as files or in a database for end users or business applications.

### When to use it?

The model deployers are optional components in the ZenML stack. They are used to deploy machine learning models to a
target environment, either a development (local) or a production (Kubernetes or cloud) environment. The model deployers are mainly used to deploy models for real-time inference use cases. With the model deployers and other stack components, you can build pipelines that are continuously trained and deployed to production.

### How model deployers slot into the stack

Here is an architecture diagram that shows how model deployers fit into the overall story of a remote stack.

![Model Deployers](../../.gitbook/assets/Remote_with_deployer.png)

#### Model Deployers Flavors

ZenML comes with a `local` MLflow model deployer which is a simple model deployer that deploys models to a local MLflow
server. Additional model deployers that can be used to deploy models on production environments are provided by
integrations:

| Model Deployer                     | Flavor    | Integration   | Notes                                                                        |
|------------------------------------|-----------|---------------|------------------------------------------------------------------------------|
| [MLflow](mlflow.md)                | `mlflow`  | `mlflow`      | Deploys ML Model locally                                                     |
| [BentoML](bentoml.md)              | `bentoml` | `bentoml`     | Build and Deploy ML models locally or for production grade (Cloud, K8s)      |
| [Seldon Core](seldon.md)           | `seldon`  | `seldon Core` | Built on top of Kubernetes to deploy models for production grade environment |
| [Hugging Face](huggingface.md) | `huggingface` | `huggingface` | Deploys ML model on Hugging Face Inference Endpoints |
| [Databricks](databricks.md) | `databricks` | `databricks` | Deploying models to Databricks Inference Endpoints with Databricks |
| [vLLM](vllm.md)                | `vllm`  | `vllm`      | Deploys LLM using vLLM locally |
| [Custom Implementation](custom.md) | _custom_  |               | Extend the Artifact Store abstraction and provide your own implementation    |

{% hint style="info" %}
Every model deployer may have different attributes that must be configured in order to interact with the model serving
tool, framework, or platform (e.g. hostnames, URLs, references to credentials, and other client-related configuration
parameters). The following example shows the configuration of the MLflow and Seldon Core model deployers:

```shell
# Configure MLflow model deployer
zenml model-deployer register mlflow --flavor=mlflow

# Configure Seldon Core model deployer
zenml model-deployer register seldon --flavor=seldon \
--kubernetes_context=zenml-eks --kubernetes_namespace=zenml-workloads \
--base_url=http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com
...
```

{% endhint %}

#### The role that a model deployer plays in a ZenML Stack

* Seamless Model Deployment: Facilitates the deployment of machine learning models to various serving environments, such as local servers, Kubernetes clusters, or cloud platforms, ensuring that models can be deployed and managed efficiently in accordance with the specific requirements of the serving infrastructure by holds all the stack-related configuration attributes required to interact with the remote model serving tool, service, or platform (e.g. hostnames, URLs, references to credentials, and other client-related configuration parameters). The following are examples of configuring the MLflow and Seldon Core Model Deployers and registering them as a Stack component:

   ```bash
   zenml integration install mlflow
   zenml model-deployer register mlflow --flavor=mlflow
   zenml stack register local_with_mlflow -m default -a default -o default -d mlflow --set
   ```

   ```bash
   zenml integration install seldon
   zenml model-deployer register seldon --flavor=seldon \
   --kubernetes_context=zenml-eks --kubernetes_namespace=zenml-workloads \
   --base_url=http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com
   ...
   zenml stack register seldon_stack -m default -a aws -o default -d seldon
   ```

* Lifecycle Management: Provides mechanisms for comprehensive lifecycle management of model servers, including the ability to start, stop, and delete model servers, as well as to update existing servers with new model versions, thereby optimizing resource utilization and facilitating continuous delivery of model updates. Some core methods that can be used to interact with the remote model server include:
  - `deploy_model` - Deploys a model to the serving environment and returns a Service object that represents the deployed model server.
  - `find_model_server` - Finds and returns a list of Service objects that
    represent model servers that have been deployed to the serving environment,
    the `services` are stored in the DB and can be used as a reference to know what and where the model is deployed.
  - `stop_model_server` - Stops a model server that is currently running in the serving environment.
  - `start_model_server` - Starts a model server that has been stopped in the serving environment.
  - `delete_model_server` - Deletes a model server from the serving environment and from the DB.

{% hint style="info" %}
ZenML uses the Service object to represent a model server that has been deployed to a serving environment. The Service object is saved in the DB and can be used as a reference to know what and where the model is deployed. The Service object consists of 2 main attributes, the `config` and the `status`. The `config` attribute holds all the deployment configuration attributes required to create a new deployment, while the `status` attribute holds the operational status of the deployment, such as the last error message, the prediction URL, and the deployment status.
{% endhint %}

   ```python
   from zenml.integrations.huggingface.model_deployers import HuggingFaceModelDeployer

   model_deployer = HuggingFaceModelDeployer.get_active_model_deployer()
   services = model_deployer.find_model_server(
       pipeline_name="LLM_pipeline",
       pipeline_step_name="huggingface_model_deployer_step",
       model_name="LLAMA-7B",
   )
   if services:
       if services[0].is_running:
           print(
               f"Model server {services[0].config['model_name']} is running at {services[0].status['prediction_url']}"
              )
        else:
            print(f"Model server {services[0].config['model_name']} is not running")
            model_deployer.start_model_server(services[0])
    else:
        print("No model server found")
        service = model_deployer.deploy_model(
            pipeline_name="LLM_pipeline",
            pipeline_step_name="huggingface_model_deployer_step",
            model_name="LLAMA-7B",
            model_uri="s3://zenprojects/huggingface_model_deployer_step/output/884/huggingface",
            revision="main",
            task="text-classification",
            region="us-east-1",
            vendor="aws",
            token="huggingface_token",
            namespace="zenml-workloads",
            endpoint_type="public",
        )
        print(f"Model server {service.config['model_name']} is deployed at {service.status['prediction_url']}")
   ```

#### &#x20;How to Interact with a model deployer after deployment?

When a Model Deployer is part of the active ZenML Stack, it is also possible to interact with it from the CLI to list,
start, stop, or delete the model servers that is managed:

```
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME         ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼────────────────────────────┨
┃   ✅   │ 8cbe671b-9fce-4394-a051-68e001f92765 │ seldon_deployment_pipeline     │ seldon_model_deployer_step ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml model-deployer models describe 8cbe671b-9fce-4394-a051-68e001f92765
                          Properties of Served Model 8cbe671b-9fce-4394-a051-68e001f92765                          
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ mnist                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ s3://zenprojects/seldon_model_deployer_step/output/884/seldon                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ seldon_deployment_pipeline                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ RUN_NAME               │ seldon_deployment_pipeline-11_Apr_22-09_39_27_648527                               ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ seldon_model_deployer_step                                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/… ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ SELDON_DEPLOYMENT      │ zenml-8cbe671b-9fce-4394-a051-68e001f92765                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                                                     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │ Seldon Core deployment 'zenml-8cbe671b-9fce-4394-a051-68e001f92765' is available       ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                   │ 8cbe671b-9fce-4394-a051-68e001f92765                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml model-deployer models get-url 8cbe671b-9fce-4394-a051-68e001f92765
  Prediction URL of Served Model 8cbe671b-9fce-4394-a051-68e001f92765 is:
  http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-8cbe67
1b-9fce-4394-a051-68e001f92765/api/v0.1/predictions

$ zenml model-deployer models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

In Python, you can alternatively discover the prediction URL of a deployed model by inspecting the metadata of the step
that deployed the model:

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run("<PIPELINE_RUN_NAME>")
deployer_step = pipeline_run.steps["<NAME_OF_MODEL_DEPLOYER_STEP>"]
deployed_model_url = deployer_step.run_metadata["deployed_model_url"].value
```

The ZenML integrations that provide Model Deployer stack components also include standard pipeline steps that can
directly be inserted into any pipeline to achieve a continuous model deployment workflow. These steps take care of all
the aspects of continuously deploying models to an external server and saving the Service configuration into the
Artifact Store, where they can be loaded at a later time and re-create the initial conditions used to serve a particular
model.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
