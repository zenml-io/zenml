---
description: Deploying your pipelines to GCP Cloud Run.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# GCP Cloud Run Deployer

[GCP Cloud Run](https://cloud.google.com/run) is a fully managed serverless platform that allows you to deploy and run your code in a production-ready, repeatable cloud environment without the need to manage any infrastructure. The GCP Cloud Run deployer is a [deployer](./) flavor included in the ZenML GCP integration that deploys your pipelines to GCP Cloud Run.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML installation](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML setup may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the GCP Cloud Run deployer if:

* you're already using GCP.
* you're looking for a proven production-grade deployer.
* you're looking for a serverless solution for deploying your pipelines as HTTP micro-services.
* you want automatic scaling with pay-per-use pricing.
* you need to deploy containerized applications with minimal configuration.

## How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including a GCP Cloud Run deployer? Check out [the ZenML GCP Terraform module](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform) for a shortcut on how to deploy & register this stack component and everything else needed by it.
{% endhint %}

In order to use a GCP Cloud Run deployer, you need to first deploy [ZenML to the cloud](https://docs.zenml.io/getting-started/deploying-zenml/). It would be recommended to deploy ZenML in the same Google Cloud project as where the GCP Cloud Run infrastructure is deployed, but it is not necessary to do so. You must ensure that you are connected to the remote ZenML server before using this stack component.

The only other thing necessary to use the ZenML GCP Cloud Run deployer is enabling GCP Cloud Run-relevant APIs on the Google Cloud project.

## How to use it

To use the GCP Cloud Run deployer, you need:

*   The ZenML `gcp` integration installed. If you haven't done so, run

    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) as part of your stack.
* [GCP credentials with proper permissions](gcp-cloud-run.md#gcp-credentials-and-permissions)
* The GCP project ID and location in which you want to deploy your pipelines.

### GCP credentials and permissions

You have two different options to provide credentials to the GCP Cloud Run deployer:

* use the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with GCP
* (recommended) configure [a GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) with GCP credentials and then link the GCP Cloud Run deployer stack component to the Service Connector.

#### GCP Permissions

Regardless of the authentication method used, the credentials used with the GCP Cloud Run deployer need the following permissions in the target GCP project:

* the `roles/run.admin` role - for managing Cloud Run services
* the following permissions to manage GCP secrets are required only if the Deployer is configured to use secrets to pass sensitive information to the Cloud Run services instead of regular environment variables (i.e. if the `use_secret_manager` setting is set to `True`):
    * the unconditional `secretmanager.secrets.create` permission is required to create new secrets in the target GCP project.
    * the `roles/secretmanager.admin` role restricted to only manage secrets with a name prefix of `zenml-`. Note that this prefix is also configurable and can be changed by setting the `secret_name_prefix` setting.

    As a simpler alternative, the `roles/secretmanager.admin` role can be granted at the project level with no condition applied.

#### Configuration use-case: local `gcloud` CLI with user account

This configuration use-case assumes you have configured the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with your GCP account (i.e. by running `gcloud auth login`). It also assumes that your GCP account has [the permissions required to use the GCP Cloud Run deployer](gcp-cloud-run.md#gcp-permissions).

This is the easiest way to configure the GCP Cloud Run deployer, but it has the following drawbacks:

* the setup is not portable on other machines and reproducible by other users (i.e. other users won't be able to use the Deployer to deploy pipelines or manage your Deployments, although they would still be able to access their exposed endpoints and send HTTP requests).
* it uses the Compute Engine default service account, which is not recommended, given that it has a lot of permissions by default and is used by many other GCP services.

The deployer can be registered as follows:

```shell
zenml deployer register <DEPLOYER_NAME> \
    --flavor=gcp \
    --project=<PROJECT_ID> \
    --location=<GCP_LOCATION> \
```

#### Configuration use-case: GCP Service Connector

This use-case assumes you have already configured a GCP service account with the [permissions required to use the GCP Cloud Run deployer](gcp-cloud-run.md#gcp-permissions).

It also assumes you have already created a service account key for this service account and downloaded it to your local machine (e.g. in a `zenml-cloud-run-deployer.json` file), although there are [ways to authenticate with GCP through a GCP Service Connector that don't require a service account key](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector#external-account-gcp-workload-identity).

With the service account and the key ready, you can register [the GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) and GCP Cloud Run deployer as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@zenml-cloud-run-deployer.json --resource-type gcp-generic

zenml deployer register <DEPLOYER_NAME> \
    --flavor=gcp \
    --location=<GCP_LOCATION> \
    --connector <CONNECTOR_NAME>
```

### Configuring the stack

With the deployer registered, it can be used in the active stack:

```shell
# Register and activate a stack with the new deployer
zenml stack register <STACK_NAME> -D <DEPLOYER_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` and use it to deploy your pipeline as a Cloud Run service. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now [deploy any ZenML pipeline](https://docs.zenml.io/concepts/deployment) using the GCP Cloud Run deployer:

```shell
zenml pipeline deploy my_module.my_pipeline
```

### Additional configuration

For additional configuration of the GCP Cloud Run deployer, you can pass the following `GCPDeployerSettings` attributes defined in the `zenml.integrations.gcp.flavors.gcp_deployer_flavor` module when configuring the deployer or defining or deploying your pipeline:

* Basic settings common to all Deployers:

  * `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  * `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  * `lcm_timeout`: The maximum time in seconds to wait for the deployment lifecycle management to complete.

* GCP Cloud Run-specific settings:

  * `location` (default: `"europe-west3"`): Name of GCP region where the pipeline will be deployed. Cloud Run is available in specific regions: https://cloud.google.com/run/docs/locations
  * `service_name_prefix` (default: `"zenml-"`): Prefix for service names in Cloud Run to avoid naming conflicts.
  * `timeout_seconds` (default: `300`): Request timeout in seconds. Must be between 1 and 3600 seconds (1 hour maximum).
  * `ingress` (default: `"all"`): Ingress settings for the service. Available options: `'all'`, `'internal'`, `'internal-and-cloud-load-balancing'`.
  * `vpc_connector` (default: `None`): VPC connector for private networking. Format: `projects/PROJECT_ID/locations/LOCATION/connectors/CONNECTOR_NAME`
  * `service_account` (default: `None`): Service account email to run the Cloud Run service. If not specified, uses the default Compute Engine service account.
  * `environment_variables` (default: `{}`): Dictionary of environment variables to set in the Cloud Run service.
  * `labels` (default: `{}`): Dictionary of labels to apply to the Cloud Run service for organization and billing purposes.
  * `annotations` (default: `{}`): Dictionary of annotations to apply to the Cloud Run service for additional metadata.
  * `execution_environment` (default: `"gen2"`): Execution environment generation. Available options: `'gen1'`, `'gen2'`.
  * `traffic_allocation` (default: `{"LATEST": 100}`): Traffic allocation between revisions. Keys are revision names or `'LATEST'`, values are percentages that must sum to 100.
  * `allow_unauthenticated` (default: `True`): Whether to allow unauthenticated requests to the service. Set to `False` for private services requiring GCP specific authentication.
  * `use_secret_manager` (default: `True`): Whether to store sensitive environment variables in GCP Secret Manager instead of directly in the Cloud Run service configuration for enhanced security.
  * `secret_name_prefix` (default: `"zenml-"`): Prefix for secret names in Secret Manager to avoid naming conflicts when using Secret Manager for sensitive data.
    
Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For example, if you wanted to disable the use of GCP Secret Manager for the deployment, you would configure settings as follows:

```python
from zenml import step, pipeline
from zenml.integrations.gcp.flavors.gcp_deployer_flavor import GCPDeployerSettings

@step
def greet(name: str) -> str:
    return f"Hello {name}!"

settings = {
    "deployer": GCPDeployerSettings(
        use_secret_manager=False
    )
}

@pipeline(settings=settings)
def greet_pipeline(name: str = "John"):
    greet(name=name)
```

### Resource and scaling settings

You can specify the resource and scaling requirements for the pipeline deployment using the `ResourceSettings` class at the pipeline level, as described in our documentation on [resource settings](https://docs.zenml.io/concepts/steps_and_pipelines/configuration#resource-settings):

```python
from zenml import step, pipeline
from zenml.config import ResourceSettings

resource_settings = ResourceSettings(
    cpu_count=2,
    memory="32GB",
    min_replicas=0,
    max_replicas=10,
    max_concurrency=50
)

...

@pipeline(settings={"resources": resource_settings})
def greet_pipeline(name: str = "John"):
    greet(name=name)
```

If resource settings are not set, the default values are as follows:
* `cpu_count` is `1`
* `memory` is `2GiB`
* `min_replicas` is `1`
* `max_replicas` is `100`
* `max_concurrency` is `80`

{% hint style="warning" %}
GCP Cloud Run defines specific rules concerning allowed combinations of CPU and memory values. The following rules apply (as of October 2025):

* CPU constraints:
  * fractional CPUs: 0.08 to < 1.0 (in increments of 0.01)
  * integer CPUs: 1, 2, 4, 6, or 8 (no fractional values allowed >= 1.0)

* minimum memory requirements per CPU configuration:
  * <=1 CPU: 128 MiB minimum
  * 2 CPU: 128 MiB minimum
  * 4 CPU: 2 GiB minimum
  * 6 CPU: 4 GiB minimum
  * 8 CPU: 4 GiB minimum

For more information, see the [GCP Cloud Run documentation](https://cloud.google.com/run/docs/configuring/services/cpu).

Specifying `cpu_count` and `memory` values that are not valid according to these rules will **not** result in an error when deploying the pipeline. Instead, the values will be automatically adjusted to the nearest matching valid values that satisfy the rules. Some examples:

* `cpu_count=0.25` and `memory="100MiB"` will be adjusted to `cpu_count=0.25` and `memory="128MiB"`
* `cpu_count=1.5` and `memory` not specified will be adjusted to `cpu_count=2` and `memory="128MiB"`
* `cpu_count=6` and `memory="1GB"` will be adjusted to `cpu_count=6` and `memory="4GiB"`
{% endhint %}
