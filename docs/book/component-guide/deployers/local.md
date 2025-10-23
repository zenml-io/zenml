---
description: Deploying pipelines on your local machine as background processes.
---

# Local Deployer

The local deployer is a [deployer](./) flavor that comes built-in with ZenML and deploys pipelines on your local machine as background processes.

### When to use it

The local deployer is part of your default stack when you're first getting started with ZenML. Due to it running locally on your machine, it requires no additional setup and is easy to use and debug.

You should use the local deployer if:

* you're just getting started with ZenML and want to deploy pipelines without setting up any cloud infrastructure.
* you're writing a new pipeline and want to experiment and debug quickly

### How to deploy it

The local deployer comes with ZenML and works without any additional setup.

### How to use it

To use the local deployer, you can register it and use it in your active stack:

```shell
zenml deployer register <DEPLOYER_NAME> --flavor=local

# Register and activate a stack with the new deployer
zenml stack register <STACK_NAME> -D <DEPLOYER_NAME> ... --set
```

You can now deploy any ZenML pipeline using the local deployer:

```shell
zenml pipeline deploy --name my_deployment my_module.my_pipeline
```
### Additional configuration

For additional configuration of the Local deployer, you can pass the following `LocalDeployerSettings` attributes defined in the `zenml.deployers.local.local_deployer` module when configuring the deployer or defining or deploying your pipeline:

* Basic settings common to all Deployers:

  * `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  * `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  * `lcm_timeout`: The maximum time in seconds to wait for the deployment lifecycle management to complete.

* Settings specific to the Local deployer:

  * `port`: A custom port that the deployment server will listen on. Not set by default.
  * `allocate_port_if_busy`: If True, allocate a free port if the configured `port` is busy or not set. Defaults to True.
  * `port_range`: The range of ports to search for a free port. Defaults to `(8000, 65535)`.
  * `address`: The address that the deployment server will listen on. Defaults to `127.0.0.1`.
  * `blocking`: Whether to run the deployment in the current process instead of running it as a daemon process. Defaults to False. Use this if you want to debug issues with the deployment ASGI application itself.

Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For example, if you wanted to specify the port to use for the deployment, you would configure settings as follows:

```python
from zenml import step, pipeline
from zenml.deployers.local.local_deployer import LocalDeployerSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


settings = {
    "deployer": LocalDeployerSettings(
        port=8000
    )
}

@pipeline(settings=settings)
def greet_pipeline(name: str = "John"):
    greet(name=name)
```
