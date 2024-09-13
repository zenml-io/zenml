# zenml.integrations.mlflow package

## Subpackages

* [zenml.integrations.mlflow.experiment_trackers package](zenml.integrations.mlflow.experiment_trackers.md)
  * [Submodules](zenml.integrations.mlflow.experiment_trackers.md#submodules)
  * [zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker module](zenml.integrations.mlflow.experiment_trackers.md#zenml-integrations-mlflow-experiment-trackers-mlflow-experiment-tracker-module)
  * [Module contents](zenml.integrations.mlflow.experiment_trackers.md#module-contents)
* [zenml.integrations.mlflow.flavors package](zenml.integrations.mlflow.flavors.md)
  * [Submodules](zenml.integrations.mlflow.flavors.md#submodules)
  * [zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor module](zenml.integrations.mlflow.flavors.md#zenml-integrations-mlflow-flavors-mlflow-experiment-tracker-flavor-module)
  * [zenml.integrations.mlflow.flavors.mlflow_model_deployer_flavor module](zenml.integrations.mlflow.flavors.md#zenml-integrations-mlflow-flavors-mlflow-model-deployer-flavor-module)
  * [zenml.integrations.mlflow.flavors.mlflow_model_registry_flavor module](zenml.integrations.mlflow.flavors.md#zenml-integrations-mlflow-flavors-mlflow-model-registry-flavor-module)
  * [Module contents](zenml.integrations.mlflow.flavors.md#module-contents)
* [zenml.integrations.mlflow.model_deployers package](zenml.integrations.mlflow.model_deployers.md)
  * [Submodules](zenml.integrations.mlflow.model_deployers.md#submodules)
  * [zenml.integrations.mlflow.model_deployers.mlflow_model_deployer module](zenml.integrations.mlflow.model_deployers.md#zenml-integrations-mlflow-model-deployers-mlflow-model-deployer-module)
  * [Module contents](zenml.integrations.mlflow.model_deployers.md#module-contents)
* [zenml.integrations.mlflow.model_registries package](zenml.integrations.mlflow.model_registries.md)
  * [Submodules](zenml.integrations.mlflow.model_registries.md#submodules)
  * [zenml.integrations.mlflow.model_registries.mlflow_model_registry module](zenml.integrations.mlflow.model_registries.md#zenml-integrations-mlflow-model-registries-mlflow-model-registry-module)
  * [Module contents](zenml.integrations.mlflow.model_registries.md#module-contents)
* [zenml.integrations.mlflow.services package](zenml.integrations.mlflow.services.md)
  * [Submodules](zenml.integrations.mlflow.services.md#submodules)
  * [zenml.integrations.mlflow.services.mlflow_deployment module](zenml.integrations.mlflow.services.md#zenml-integrations-mlflow-services-mlflow-deployment-module)
  * [Module contents](zenml.integrations.mlflow.services.md#module-contents)
* [zenml.integrations.mlflow.steps package](zenml.integrations.mlflow.steps.md)
  * [Submodules](zenml.integrations.mlflow.steps.md#submodules)
  * [zenml.integrations.mlflow.steps.mlflow_deployer module](zenml.integrations.mlflow.steps.md#zenml-integrations-mlflow-steps-mlflow-deployer-module)
  * [zenml.integrations.mlflow.steps.mlflow_registry module](zenml.integrations.mlflow.steps.md#zenml-integrations-mlflow-steps-mlflow-registry-module)
  * [Module contents](zenml.integrations.mlflow.steps.md#module-contents)

## Submodules

## zenml.integrations.mlflow.mlflow_utils module

Implementation of utils specific to the MLflow integration.

### zenml.integrations.mlflow.mlflow_utils.get_missing_mlflow_experiment_tracker_error() → ValueError

Returns description of how to add an MLflow experiment tracker to your stack.

Returns:
: ValueError: If no MLflow experiment tracker is registered in the active stack.

### zenml.integrations.mlflow.mlflow_utils.get_tracking_uri() → str

Gets the MLflow tracking URI from the active experiment tracking stack component.

# noqa: DAR401

Returns:
: MLflow tracking URI.

### zenml.integrations.mlflow.mlflow_utils.is_zenml_run(run: Run) → bool

Checks if a MLflow run is a ZenML run or not.

Args:
: run: The run to check.

Returns:
: If the run is a ZenML run.

### zenml.integrations.mlflow.mlflow_utils.stop_zenml_mlflow_runs(status: str) → None

Stops active ZenML Mlflow runs.

This function stops all MLflow active runs until no active run exists or
a non-ZenML run is active.

Args:
: status: The status to set the run to.

## Module contents

Initialization for the ZenML MLflow integration.

The MLflow integrations currently enables you to use MLflow tracking as a
convenient way to visualize your experiment runs within the MLflow UI.

### *class* zenml.integrations.mlflow.MlflowIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of MLflow integration for ZenML.

#### NAME *= 'mlflow'*

#### REQUIREMENTS *: List[str]* *= ['mlflow>=2.1.1,<3', 'python-rapidjson<1.15', 'pydantic>=2.8.0,<2.9.0', 'mlserver>=1.3.3', 'mlserver-mlflow>=1.3.3', 'numpy<2.0.0', 'pandas>=2.0.0', 'mlserver>=1.3.3', 'mlserver-mlflow>=1.3.3', 'numpy<2.0.0', 'pandas>=2.0.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['python-rapidjson', 'pydantic', 'numpy', 'pandas']*

#### *classmethod* activate() → None

Activate the MLflow integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the MLflow integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
