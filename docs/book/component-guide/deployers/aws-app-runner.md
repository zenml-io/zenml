---
description: Deploying your pipelines to AWS App Runner.
---

# AWS App Runner Deployer

[AWS App Runner](https://aws.amazon.com/apprunner/) is a fully managed serverless platform that allows you to deploy and run your code in a production-ready, repeatable cloud environment without the need to manage any infrastructure. The AWS App Runner deployer is a [deployer](./) flavor included in the ZenML AWS integration that deploys your pipelines to AWS App Runner.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the AWS App Runner deployer if:

* you're already using AWS.
* you're looking for a proven production-grade deployer.
* you're looking for a serverless solution for deploying your pipelines as HTTP micro-services.
* you want automatic scaling with pay-per-use pricing.
* you need to deploy containerized applications with minimal configuration.

## How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including an AWS App Runner deployer? Check out [the ZenML AWS Terraform module](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform) for a shortcut on how to deploy & register this stack component and everything else needed by it.
{% endhint %}

{% hint style="warning" %}
App Runner is available only in specific regions: https://docs.aws.amazon.com/apprunner/latest/dg/regions.html
{% endhint %}

In order to use an AWS App Runner deployer, you need to first deploy [ZenML to the cloud](https://docs.zenml.io/getting-started/deploying-zenml/). It would be recommended to deploy ZenML in the same AWS account and region as where the AWS App Runner infrastructure is deployed, but it is not necessary to do so. You must ensure that you are connected to the remote ZenML server before using this stack component.

The AWS App Runner deployer requires that you have the necessary IAM permissions to create and manage App Runner services, and optionally access to AWS Secrets Manager and CloudWatch Logs for enhanced functionality.

## How to use it

To use the AWS App Runner deployer, you need:

*   The ZenML `aws` integration installed. If you haven't done so, run

    ```shell
    zenml integration install aws
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) as part of your stack (**NOTE**:must be Amazon ECR or ECR Public).
* [AWS credentials with proper permissions](aws-app-runner.md#aws-credentials-and-permissions) to create and manage the App Runner services themselves.
* When using a private ECR container registry, an IAM role with specific ECR permissions should also be created and configured as [the App Runner access role](https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-roles) (see [Required IAM Permissions](#required-iam-permissions) below). If this is not configured, App Runner will attempt to use the default `AWSServiceRoleForAppRunner` service role, which may not have ECR access permissions.
* If opting the AWS Secrets Manager to store sensitive information (enabled by default), an IAM role with specific Secrets Manager permissions should also be created and configured as [the App Runner instance role](https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-roles) (see [Required IAM Permissions](#required-iam-permissions) below). If this is not configured, App Runner will attempt to use the default `AWSServiceRoleForAppRunner` service role, which may not have Secrets Manager access permissions.
* The AWS region in which you want to deploy your pipelines.

### AWS credentials and permissions

You have two different options to provide credentials to the AWS App Runner deployer:

* use the [AWS CLI](https://aws.amazon.com/cli/) to authenticate locally with AWS
* (recommended) configure [an AWS Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/aws-service-connector) with AWS credentials and then link the AWS App Runner deployer stack component to the Service Connector.

#### AWS Permissions

Depending on how you configure the AWS App Runner deployer, there can be at most three different sets of permissions involved:
* the client permissions - these are the permissions needed by the Deployer stack component itself to interact with the App Runner service and optionally to manage AWS Secrets Manager secrets. These permissions need to come from either the local AWS SDK or the AWS Service Connector:
    * the permissions in the `AWSAppRunnerFullAccess` policy.
    * the following permissions for AWS Secrets Manager are also required if the deployer is configured to use secrets to pass sensitive information to the App Runner services instead of regular environment variables (i.e. if the `use_secrets_manager` setting is set to `True`):
        * `secretsmanager:CreateSecret`
        * `secretsmanager:UpdateSecret`
        * `secretsmanager:DeleteSecret`
        * `secretsmanager:DescribeSecret`
        * `secretsmanager:GetSecretValue`
        * `secretsmanager:PutSecretValue`
        * `secretsmanager:TagResource`

    These permissions should additionally be restricted to only allow access to secrets with a name starting with `zenml-` in the target region and account. Note that this prefix is also configurable and can be changed by setting the `secret_name_prefix` setting.

    * CloudWatch Logs permissions (for log retrieval):
        * `logs:DescribeLogGroups`
        * `logs:DescribeLogStreams`
        * `logs:GetLogEvents`

    * `iam:PassRole` permission granted for the App Runner access role and instance role, if they are also configured (see below).

* [the App Runner access role](https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-roles) - this is a role that App Runner uses for accessing images in Amazon ECR in your account. It's only required to access an image in Amazon ECR, and isn't required with Amazon ECR Public. This role should include the `AWSAppRunnerServicePolicyForECRAccess` policy or something similar restricted to the target ECR repository.

* [the App Runner instance role](https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-roles) - this is a role that the App Runner instances themselves use for accessing the AWS Secrets Manager secrets. It's only required if you use the AWS Secrets Manager to store sensitive information (i.e. if you keep the `use_secrets_manager` option set to `True` in the [deployer settings](aws-app-runner.md#additional-configuration)). This role should include the `secretsmanager:GetSecretValue` permission optionally restricted to only allow access to secrets with a name starting with `zenml-` in the target region and account. Note that this prefix is also configurable and can be changed by setting the `secret_name_prefix` setting.

#### Configuration use-case: local AWS CLI with user account

This configuration use-case assumes you have configured the [AWS CLI](https://aws.amazon.com/cli/) to authenticate locally with your AWS account (i.e. by running `aws configure`). It also assumes that your AWS account has [the client permissions required to use the AWS App Runner deployer](aws-app-runner.md#aws-permissions).

This is the easiest way to configure the AWS App Runner deployer, but it has the following drawbacks:

* the setup is not portable on other machines and reproducible by other users (i.e. other users won't be able to use the Deployer to deploy pipelines or manage your Deployments, although they would still be able to access their exposed endpoints and send HTTP requests).
* it uses your personal AWS credentials, which may have broader permissions than necessary for the deployer.


The deployer can be registered as follows:

```shell
zenml deployer register <DEPLOYER_NAME> \
    --flavor=aws \
    --region=<AWS_REGION> \
    --instance_role_arn=<INSTANCE_ROLE_ARN> \
    --access_role_arn=<ACCESS_ROLE_ARN>
```

#### Configuration use-case: AWS Service Connector

This use-case assumes you have already configured an AWS IAM user or role with the [client permissions required to use the AWS App Runner deployer](aws-app-runner.md#aws-permissions).

It also assumes you have already created access keys for this IAM user and have them available (access key ID and secret access key), although there are [ways to authenticate with AWS through an AWS Service Connector that don't require long-term access keys](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/aws-service-connector#aws-iam-role).

With the IAM credentials ready, you can register [the AWS Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/aws-service-connector) and AWS App Runner deployer as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type aws --auth-method=secret-key --aws_access_key_id=<ACCESS_KEY_ID> --aws_secret_access_key=<SECRET_ACCESS_KEY> --region=<AWS_REGION> --resource-type aws-generic

zenml deployer register <DEPLOYER_NAME> \
    --flavor=aws \
    --instance_role_arn=<INSTANCE_ROLE_ARN> \
    --access_role_arn=<ACCESS_ROLE_ARN> \
    --connector <CONNECTOR_NAME>
```


### Configuring the stack

With the deployer registered, it can be used in the active stack:

```shell
# Register and activate a stack with the new deployer
zenml stack register <STACK_NAME> -D <DEPLOYER_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` and use it to deploy your pipeline as an App Runner service. The container registry must be Amazon ECR (private) or ECR Public. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now deploy any ZenML pipeline using the AWS App Runner deployer:

```shell
zenml pipeline deploy my_module.my_pipeline
```

### Additional configuration

For additional configuration of the AWS App Runner deployer, you can pass the following `AWSDeployerSettings` attributes defined in the `zenml.integrations.aws.flavors.aws_deployer_flavor` module when configuring the deployer or defining or deploying your pipeline:

* Basic settings common to all Deployers:

  * `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  * `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  * `lcm_timeout`: The maximum time in seconds to wait for the deployment lifecycle management to complete.

* AWS App Runner-specific settings:

  * `region` (default: `None`): AWS region where the App Runner service will be deployed. If not specified, the region will be determined from the authenticated session. App Runner is available in specific regions: https://docs.aws.amazon.com/apprunner/latest/dg/regions.html. Setting this has no effect if the deployer is configured with an AWS Service Connector.
  * `service_name_prefix` (default: `"zenml-"`): Prefix for service names in App Runner to avoid naming conflicts.
  * `port` (default: `8080`): Port on which the container listens for requests.
  * `health_check_grace_period_seconds` (default: `20`): Grace period for health checks in seconds. Range: 0-20.
  * `health_check_interval_seconds` (default: `10`): Interval between health checks in seconds. Range: 1-20.
  * `health_check_path` (default: `"/health"`): Health check path for the App Runner service.
  * `health_check_protocol` (default: `"TCP"`): Health check protocol. Options: 'TCP', 'HTTP'.
  * `health_check_timeout_seconds` (default: `2`): Timeout for health checks in seconds. Range: 1-20.
  * `health_check_healthy_threshold` (default: `1`): Number of consecutive successful health checks required.
  * `health_check_unhealthy_threshold` (default: `5`): Number of consecutive failed health checks before unhealthy.
  * `is_publicly_accessible` (default: `True`): Whether the App Runner service is publicly accessible.
  * `ingress_vpc_configuration` (default: `None`): VPC configuration for private App Runner services. JSON string with VpcId, VpcEndpointId, and VpcIngressConnectionName.
  * `environment_variables` (default: `{}`): Dictionary of environment variables to set in the App Runner service.
  * `tags` (default: `{}`): Dictionary of tags to apply to the App Runner service.
  * `use_secrets_manager` (default: `True`): Whether to store sensitive environment variables in AWS Secrets Manager instead of directly in the App Runner service configuration. When this is set to `True`, the deployer will also require additional permissions to access the AWS Secrets Manager secrets and an [App Runner instance role](https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-roles) to be configured as [the App Runner instance role](aws-app-runner.md#aws-permissions).
  * `secret_name_prefix` (default: `"zenml-"`): Prefix for secret names in Secrets Manager to avoid naming conflicts.
  * `observability_configuration_arn` (default: `None`): ARN of the observability configuration to associate with the App Runner service.
  * `encryption_kms_key` (default: `None`): KMS key ARN for encrypting App Runner service data.
  * `instance_role_arn` (default: `None`): ARN of the IAM role to assign to the App Runner service instances. Required if the `use_secrets_manager` setting is set to `True`.
  * `access_role_arn` (default: `None`): ARN of the IAM role that App Runner uses to access the image repository (ECR). Required for private ECR repositories.
  * `strict_resource_matching` (default: `False`): Whether to enforce strict matching of resource requirements to AWS App Runner supported CPU and memory combinations. When True, raises an error if no exact match is found. When False, automatically selects the closest matching supported combination.
    
Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For example, if you wanted to disable the use of AWS Secrets Manager for the deployment, you would configure settings as follows:

```python
from zenml import step, pipeline
from zenml.integrations.aws.flavors.aws_deployer_flavor import AWSDeployerSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


settings = {
    "deployer": AWSDeployerSettings(
        use_secrets_manager=False
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
    cpu_count=1.0,
    memory="2GB",
    min_replicas=4,
    max_replicas=25,
    max_concurrency=100
)

...

@pipeline(settings={"resources": resource_settings})
def greet_pipeline(name: str = "John"):
    greet(name=name)
```

{% hint style="warning" %}
AWS App Runner defines specific rules concerning allowed combinations of CPU (vCPU) and memory (GB) values. For more information, see the [AWS App Runner documentation](https://docs.aws.amazon.com/apprunner/latest/dg/architecture.html#architecture.vcpu-memory).

Supported combinations include:
- 0.25 vCPU: 0.5 GB, 1 GB
- 0.5 vCPU: 1 GB
- 1 vCPU: 2 GB, 3 GB, 4 GB
- 2 vCPU: 4 GB, 6 GB
- 4 vCPU: 8 GB, 10 GB, 12 GB

By default, specifying `cpu_count` and `memory` values that are not valid according to these rules will **not** result in an error when deploying the pipeline. Instead, the values will be automatically adjusted to the nearest matching valid combination using an algorithm that prioritizes CPU requirements over memory requirements and aims to minimize waste. You can enable `strict_resource_matching=True` in the deployer settings to enforce exact matches and raise an error if no valid combination is found. You can also override and configure your own allowed resource combinations in the deployer's configuration via the `resource_combinations` option.
{% endhint %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
