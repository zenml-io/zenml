# zenml.integrations.kubeflow package

## Subpackages

* [zenml.integrations.kubeflow.flavors package](zenml.integrations.kubeflow.flavors.md)
  * [Submodules](zenml.integrations.kubeflow.flavors.md#submodules)
  * [zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor module](zenml.integrations.kubeflow.flavors.md#zenml-integrations-kubeflow-flavors-kubeflow-orchestrator-flavor-module)
  * [Module contents](zenml.integrations.kubeflow.flavors.md#module-contents)
* [zenml.integrations.kubeflow.orchestrators package](zenml.integrations.kubeflow.orchestrators.md)
  * [Submodules](zenml.integrations.kubeflow.orchestrators.md#submodules)
  * [zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator module](zenml.integrations.kubeflow.orchestrators.md#zenml-integrations-kubeflow-orchestrators-kubeflow-orchestrator-module)
  * [zenml.integrations.kubeflow.orchestrators.local_deployment_utils module](zenml.integrations.kubeflow.orchestrators.md#zenml-integrations-kubeflow-orchestrators-local-deployment-utils-module)
  * [zenml.integrations.kubeflow.orchestrators.test_kfp module](zenml.integrations.kubeflow.orchestrators.md#zenml-integrations-kubeflow-orchestrators-test-kfp-module)
  * [zenml.integrations.kubeflow.orchestrators.test_kfp2 module](zenml.integrations.kubeflow.orchestrators.md#zenml-integrations-kubeflow-orchestrators-test-kfp2-module)
  * [Module contents](zenml.integrations.kubeflow.orchestrators.md#module-contents)

## Module contents

Initialization of the Kubeflow integration for ZenML.

The Kubeflow integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubeflow orchestrator with
the CLI tool.

### *class* zenml.integrations.kubeflow.KubeflowIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Kubeflow Integration for ZenML.

#### NAME *= 'kubeflow'*

#### REQUIREMENTS *: List[str]* *= ['kfp>=2.6.0', 'kfp-kubernetes>=1.1.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kfp']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Kubeflow integration.

Returns:
: List of stack component flavors for this integration.
