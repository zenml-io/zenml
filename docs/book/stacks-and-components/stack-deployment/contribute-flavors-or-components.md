---
description: Creating your custom stack component solutions.
---

# Contribute flavors or components

Before you can start contributing, it is important to know that the stack component deploy CLI also makes use of the stack recipes (specifically, the modular stack recipes) in the background. Thus, contributing a new deployment option for both the deployment methods that we have seen, involves making a contribution to the base recipe.

You can refer to the [`CONTRIBUTING.md`](https://github.com/zenml-io/mlstacks/blob/main/CONTRIBUTING.md) on the `mlstacks` repo to get an overview of how all recipes are designed in general but here are instructions for contributing to the modular recipes specifically.

## Adding new MLOps tools

* Clone the [`mlstacks`](https://github.com/zenml-io/mlstacks) repo and create a branch off `develop`.
* Every file inside the modular recipes represents a tool and all code pertaining to the deployment of it resides there. Create a new file with a name that reflects what would be deployed.
* Populate this file with all the terraform code that is relevant to the component. Make sure any dependencies are also included in the same file.
* Add any local values that you might need here to the `locals.tf` file.
* If you want to enable users to set any configuration parameters through the CLI, add those variables to the `variables.tf` file. You can take a look at existing variables like `mlflow_bucket` to get an idea of how to do this.
* Now, add a variable that allows the user to enable this service, to the `variables.tf` file. The format for the name is `enable_<STACK_COMPONENT>_<FLAVOR>`
* You also need to populate the `outputs.tf` file with information that a stack component registration for your new component might need. This is used by the stack component deploy CLI.
* Add a block to the `output_file.tf` file that corresponds to your component. This is the file that gets generated on a successful `stack recipe deploy` event and can be imported as a ZenML stack.
* Finally, contribute a PR back to `develop`! 🥳

Once merged, this should allow other people to use your new component while deploying through the `zenml stack recipe deploy ..-modular` flow. To enable integration with the stack component deploy CLI, you need to also contribute to the `zenml-io/zenml` repo.

## Enabling the stack component deploy CLI

To enable the stack component deploy CLI to work with your new component, you need to add a new flag to the [`deploy_stack_component_command`](https://github.com/zenml-io/zenml/blob/6265248f7c268deb2ac6d5a268763a9d287ac845/src/zenml/cli/stack\_components.py#L1114) in the `src/zenml/cli/stack_components.py` file.

Specifically, you can edit the following [dictionary](https://github.com/zenml-io/zenml/blob/6265248f7c268deb2ac6d5a268763a9d287ac845/src/zenml/cli/stack\_components.py#L1114) to include your flavor and stack component information.

{% code overflow="wrap" %}
```
allowed_flavors = {
            "experiment_tracker": ["mlflow"],
            "model_deployer": ["seldon"],
            "artifact_store": ["s3", "gcp", "minio"],
            "container_registry": ["gcp", "aws"],
            "orchestrator": ["kubernetes", "kubeflow", ...],
            "step_operator": ["sagemaker", "vertex"],
        }
```
{% endcode %}

This should make the ZenML CLI aware of your new contribution.

Happy contributing! 🥰

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
