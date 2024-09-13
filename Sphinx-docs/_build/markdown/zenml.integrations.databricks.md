# zenml.integrations.databricks package

## Subpackages

* [zenml.integrations.databricks.flavors package](zenml.integrations.databricks.flavors.md)
  * [Submodules](zenml.integrations.databricks.flavors.md#submodules)
  * [zenml.integrations.databricks.flavors.databricks_model_deployer_flavor module](zenml.integrations.databricks.flavors.md#zenml-integrations-databricks-flavors-databricks-model-deployer-flavor-module)
  * [zenml.integrations.databricks.flavors.databricks_orchestrator_flavor module](zenml.integrations.databricks.flavors.md#zenml-integrations-databricks-flavors-databricks-orchestrator-flavor-module)
  * [Module contents](zenml.integrations.databricks.flavors.md#module-contents)
* [zenml.integrations.databricks.model_deployers package](zenml.integrations.databricks.model_deployers.md)
  * [Submodules](zenml.integrations.databricks.model_deployers.md#submodules)
  * [zenml.integrations.databricks.model_deployers.databricks_model_deployer module](zenml.integrations.databricks.model_deployers.md#zenml-integrations-databricks-model-deployers-databricks-model-deployer-module)
  * [Module contents](zenml.integrations.databricks.model_deployers.md#module-contents)
* [zenml.integrations.databricks.orchestrators package](zenml.integrations.databricks.orchestrators.md)
  * [Submodules](zenml.integrations.databricks.orchestrators.md#submodules)
  * [zenml.integrations.databricks.orchestrators.databricks_orchestrator module](zenml.integrations.databricks.orchestrators.md#zenml-integrations-databricks-orchestrators-databricks-orchestrator-module)
  * [zenml.integrations.databricks.orchestrators.databricks_orchestrator_entrypoint_config module](zenml.integrations.databricks.orchestrators.md#zenml-integrations-databricks-orchestrators-databricks-orchestrator-entrypoint-config-module)
  * [Module contents](zenml.integrations.databricks.orchestrators.md#module-contents)
* [zenml.integrations.databricks.services package](zenml.integrations.databricks.services.md)
  * [Submodules](zenml.integrations.databricks.services.md#submodules)
  * [zenml.integrations.databricks.services.databricks_deployment module](zenml.integrations.databricks.services.md#zenml-integrations-databricks-services-databricks-deployment-module)
  * [Module contents](zenml.integrations.databricks.services.md#module-contents)
* [zenml.integrations.databricks.utils package](zenml.integrations.databricks.utils.md)
  * [Submodules](zenml.integrations.databricks.utils.md#submodules)
  * [zenml.integrations.databricks.utils.databricks_utils module](zenml.integrations.databricks.utils.md#module-zenml.integrations.databricks.utils.databricks_utils)
    * [`convert_step_to_task()`](zenml.integrations.databricks.utils.md#zenml.integrations.databricks.utils.databricks_utils.convert_step_to_task)
    * [`sanitize_labels()`](zenml.integrations.databricks.utils.md#zenml.integrations.databricks.utils.databricks_utils.sanitize_labels)
  * [Module contents](zenml.integrations.databricks.utils.md#module-zenml.integrations.databricks.utils)

## Module contents

Initialization of the Databricks integration for ZenML.

### *class* zenml.integrations.databricks.DatabricksIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Databricks Integration for ZenML.

#### NAME *= 'databricks'*

#### REQUIREMENTS *: List[str]* *= ['databricks-sdk==0.28.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['numpy', 'pandas']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Databricks integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
