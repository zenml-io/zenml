---
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
target environment either a development (local) or a production (Kubernetes), the model deployers are mainly used to
deploy models for real-time inference use cases. With the model deployers and other stack components, you can build
pipelines that are continuously trained and deployed to production.

### How they experiment trackers slot into the stack

Here is an architecture diagram that shows how model deployers fit into the overall story of a remote stack.

![Model Deployers](../../../.gitbook/assets/Remote_with_deployer.png)

#### Model Deployers Flavors

ZenML comes with a `local` MLflow model deployer which is a simple model deployer that deploys models to a local MLflow
server. Additional model deployers that can be used to deploy models on production environments are provided by
integrations:

| Model Deployer                     | Flavor    | Integration   | Notes                                                                        |
|------------------------------------|-----------|---------------|------------------------------------------------------------------------------|
| [MLflow](mlflow.md)                | `mlflow`  | `mlflow`      | Deploys ML Model locally                                                     |
| [BentoML](bentoml.md)              | `bentoml` | `bentoml`     | Build and Deploy ML models locally or for production grade (Cloud, K8s)      |
| [Seldon Core](seldon.md)           | `seldon`  | `seldon Core` | Built on top of Kubernetes to deploy models for production grade environment |
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

1. Holds all the stack-related configuration attributes required to interact with the remote model serving tool,
   service, or platform (e.g. hostnames, URLs, references to credentials, and other client-related configuration
   parameters). The following are examples of configuring the MLflow and Seldon Core Model Deployers and registering
   them as a Stack component:

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
2. Implements the continuous deployment logic necessary to deploy models in a way that updates an existing model server
   that is already serving a previous version of the same model instead of creating a new model server for every new
   model version. Every model server that the Model Deployer provisions externally to deploy a model is represented
   internally as a `Service` object that may be accessed for visibility and control over a single model deployment. This
   functionality can be consumed directly from ZenML pipeline steps, but it can also be used outside the pipeline to
   deploy ad-hoc models. See the [seldon_model_deployer_step](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-seldon/#zenml.integrations.seldon.steps.seldon_deployer.seldon_model_deployer_step) for an example of using the Seldon Core Model Deployer to deploy a model inside a ZenML pipeline step.
3. Acts as a registry for all Services that represent remote model servers. External model deployment servers can be
   listed and filtered using a variety of criteria, such as the name of the model or the names of the pipeline and step
   that was used to deploy the model. The Service objects returned by the Model Deployer can be used to interact with
   the remote model server, e.g. to get the operational status of a model server, the prediction URI that it exposes, or
   to stop or delete a model server:

   ```python
   from zenml.integrations.seldon.model_deployers import SeldonModelDeployer

   model_deployer = SeldonModelDeployer.get_active_model_deployer()
   services = model_deployer.find_model_server(
       pipeline_name="continuous-deployment-pipeline",
       pipeline_step_name="seldon_model_deployer_step",
       model_name="my-model",
   )
   if services:
       if services[0].is_running:
           print(
               f"Seldon deployment service started and reachable at:\n"
               f"    {services[0].prediction_url}\n"
           )
       elif services[0].is_failed:
           print(
               f"Seldon deployment service is in a failure state. "
               f"The last error message was: {services[0].status.last_error}"
           )
       else:
           print(f"Seldon deployment service is not running")

           # start the service
           services[0].start(timeout=100)

       # delete the service
       model_deployer.delete_service(services[0].uuid, timeout=100, force=False)
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
deployed_model_url = deployer_step.metadata["deployed_model_url"].value
```

Services can be passed through steps like any other object, and used to interact with the external systems that they
represent:

```python
from zenml import step


@step
def my_step(my_service: MyService) -> ...:
    if not my_service.is_running:
        my_service.start()  # starts service
    my_service.stop()  # stops service
```

The ZenML integrations that provide Model Deployer stack components also include standard pipeline steps that can
directly be inserted into any pipeline to achieve a continuous model deployment workflow. These steps take care of all
the aspects of continuously deploying models to an external server and saving the Service configuration into the
Artifact Store, where they can be loaded at a later time and re-create the initial conditions used to serve a particular
model.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
