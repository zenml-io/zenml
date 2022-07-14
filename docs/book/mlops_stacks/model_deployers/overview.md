---
description: Make your ML Models available to serve real-time predictions with Model Deployers.
---

Models Deployment is the process of making a machine learning model available to make predictions and decisions on real world data. Getting predictions from trained models can be done in different ways depending on the use-case, a batch prediction is used to generate prediction for a large amount of data at once, while a real-time prediction is used to generate predictions for a single data point at a time.

With ZenML you can achieve batch prediction by building a pipeline that generates predictions for a large amount of data at once. For the real-time prediction use-case you can use model deployers.

Model deployers are stack components responsible for online model serving. Online serving is the process of hosting and loading machine-learning models as part of a managed web service and providing access to the models through an API endpoint like HTTP or GRPC. Once deployed, you can send inference requests to the model through the web service's API and receive fast, low-latency responses.

There are three major roles that a Model Deployer plays in a ZenML Stack:

1. it holds all the stack related configuration attributes required to
   interact with the remote model serving tool, service or platform (e.g.
   hostnames, URLs, references to credentials, other client related
   configuration parameters). The following are examples of configuring the
   MLflow
   and Seldon Core Model Deployers and registering them as a Stack component:

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

2. it implements the continuous deployment logic necessary to deploy models
   in a way that updates an existing model server that is already serving a
   previous version of the same model instead of creating a new model server
   for every new model version. Every model server that the Model Deployer
   provisions externally to deploy a model is represented internally as a
   `Service` object that may be accessed for visibility and control over
   a single model deployment. This functionality can be consumed directly
   from ZenML pipeline steps, but it can also be used outside of the pipeline
   to deploy ad-hoc models. The following code is an example of using the
   Seldon Core Model Deployer to deploy a model inside a ZenML pipeline step:

    ```python
    from zenml.artifacts import ModelArtifact
    from zenml.environment import Environment
    from zenml.integrations.seldon.model_deployers import SeldonModelDeployer
    from zenml.integrations.seldon.services.seldon_deployment import (
      SeldonDeploymentConfig,
      SeldonDeploymentService,
    )
    from zenml.steps import (
      STEP_ENVIRONMENT_NAME,
      StepContext,
      step,
    )
    
    @step(enable_cache=True)
    def seldon_model_deployer_step(
      context: StepContext,
      model: ModelArtifact,
    ) -> SeldonDeploymentService:
      model_deployer = SeldonModelDeployer.get_active_model_deployer()
    
      # get pipeline name, step name and run id
      step_env = Environment()[STEP_ENVIRONMENT_NAME]
    
      service_config=SeldonDeploymentConfig(
          model_uri=model.uri,
          model_name="my-model",
          replicas=1,
          implementation="TENSORFLOW_SERVER",
          secret_name="seldon-secret",
          pipeline_name = step_env.pipeline_name,
          pipeline_run_id = step_env.pipeline_run_id,
          pipeline_step_name = step_env.step_name,
      )
    
      service = model_deployer.deploy_model(
          service_config, replace=True, timeout=300
      )
    
      print(
          f"Seldon deployment service started and reachable at:\n"
          f"    {service.prediction_url}\n"
      )
    
      return service
    ```

3. the Model Deployer acts as a registry for all Services that represent remote
   model servers. External model deployment servers can be listed and filtered
   using
   a variety of criteria, such as the name of the model or the names of the
   pipeline and step
   that was used to deploy the model. The Service objects returned by the Model
   Deployer
   can be used to interact with the remote model server, e.g. to get the
   operational
   status of a model server, the prediction URI that it exposes, or to stop or
   delete a model server:

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

When a Model Deployer is part of the active ZenML Stack, it is also possible to
interact with it from the CLI to list, start, stop or delete the model servers
that is manages:

```
$ zenml served-models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME         ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼────────────────────────────┨
┃   ✅   │ 8cbe671b-9fce-4394-a051-68e001f92765 │ continuous_deployment_pipeline │ seldon_model_deployer_step ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml served-models describe 8cbe671b-9fce-4394-a051-68e001f92765
                          Properties of Served Model 8cbe671b-9fce-4394-a051-68e001f92765                          
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ mnist                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ s3://zenfiles/seldon_model_deployer_step/output/884/seldon                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ continuous_deployment_pipeline                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_RUN_ID        │ continuous_deployment_pipeline-11_Apr_22-09_39_27_648527                               ┃
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

$ zenml served-models get-url 8cbe671b-9fce-4394-a051-68e001f92765
  Prediction URL of Served Model 8cbe671b-9fce-4394-a051-68e001f92765 is:
  http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-8cbe67
1b-9fce-4394-a051-68e001f92765/api/v0.1/predictions

$ zenml served-models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

Services can be passed through steps like any other object, and used to interact
with the external systems that
they represent:

```python
from zenml.steps import step

@step
def my_step(my_service: MyService) -> ...:
    if not my_service.is_running:
        my_service.start()  # starts service
    my_service.stop()  # stops service
```

The ZenML integrations that provide Model Deployer stack components also include
standard pipeline steps that can directly be inserted into any pipeline to achieve
a continuous model deployment workflow. These steps take care of all the aspects
of continuously deploying models to an external server and saving the Service
configuration into the Artifact Store, where they can be loaded at a later time
and re-create the initial conditions used to serve a particular model.

## When to use it

The model deployers are optional components in the ZenML stack. They are used to
deploy machine learning models to a target environment either a development (local) 
or a production (Kubernetes), the model deployers are mainly used to deploy models 
for real time inference use cases. With the model deployers and other stack components,
you can build pipelines that are continuously trained and deployed to a production.

## Model Deployers Flavors

ZenML comes with a `local` MLFlow model deployer which is a simple model deployer that
deploys models to a local MLFlow server. Additional model deployers that can be used
to deploy models on production environments are provided by integrations:

| Model Deployer | Flavor | Integration | Notes             |
|----------------|--------|-------------|-------------------|
| [MLFlow](./mlflow.md) | `mlflow` | `mlflow` | Deploys ML Model locally |
| [Seldon Core](./seldon.md) | `seldon` | `seldon Core` | Built on top of Kubernetes to deploy models for production grade environment |
| [KServe](./kserve.md) | `kserve` | `kserve` | Kubernetes based model deployment framework |
| [Custom Implementation](./custom.md) | _custom_ |  | Extend the Artifact Store abstraction and provide your own implementation |

{% hint style="info" %}
Every model deployer may have different attributes that must be configured in order to
interact with the model serving tool, framework or platform (e.g. hostnames, URLs, references to credentials, other client related configuration parameters). The following example shows the configuration of the MLFlow 
and Seldon Core model deployers:

```shell
# Configure MLFlow model deployer
zenml model-deployer register mlflow --flavor=mlflow

# Configure Seldon Core model deployer
zenml model-deployer register seldon --flavor=seldon \
--kubernetes_context=zenml-eks --kubernetes_namespace=zenml-workloads \
--base_url=http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com
...
```
{% endhint %}