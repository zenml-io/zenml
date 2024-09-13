# zenml.integrations.airflow package

## Subpackages

* [zenml.integrations.airflow.flavors package](zenml.integrations.airflow.flavors.md)
  * [Submodules](zenml.integrations.airflow.flavors.md#submodules)
  * [zenml.integrations.airflow.flavors.airflow_orchestrator_flavor module](zenml.integrations.airflow.flavors.md#zenml-integrations-airflow-flavors-airflow-orchestrator-flavor-module)
  * [Module contents](zenml.integrations.airflow.flavors.md#module-contents)
* [zenml.integrations.airflow.orchestrators package](zenml.integrations.airflow.orchestrators.md)
  * [Submodules](zenml.integrations.airflow.orchestrators.md#submodules)
  * [zenml.integrations.airflow.orchestrators.airflow_orchestrator module](zenml.integrations.airflow.orchestrators.md#zenml-integrations-airflow-orchestrators-airflow-orchestrator-module)
  * [zenml.integrations.airflow.orchestrators.dag_generator module](zenml.integrations.airflow.orchestrators.md#zenml-integrations-airflow-orchestrators-dag-generator-module)
  * [Module contents](zenml.integrations.airflow.orchestrators.md#module-contents)

## Module contents

Airflow integration for ZenML.

The Airflow integration powers an alternative orchestrator.

### *class* zenml.integrations.airflow.AirflowIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Airflow Integration for ZenML.

#### NAME *= 'airflow'*

#### REQUIREMENTS *: List[str]* *= []*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Airflow integration.

Returns:
: List of stack component flavors for this integration.
