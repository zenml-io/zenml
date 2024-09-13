# zenml.integrations.neptune package

## Subpackages

* [zenml.integrations.neptune.experiment_trackers package](zenml.integrations.neptune.experiment_trackers.md)
  * [Submodules](zenml.integrations.neptune.experiment_trackers.md#submodules)
  * [zenml.integrations.neptune.experiment_trackers.neptune_experiment_tracker module](zenml.integrations.neptune.experiment_trackers.md#zenml-integrations-neptune-experiment-trackers-neptune-experiment-tracker-module)
  * [zenml.integrations.neptune.experiment_trackers.run_state module](zenml.integrations.neptune.experiment_trackers.md#zenml-integrations-neptune-experiment-trackers-run-state-module)
  * [Module contents](zenml.integrations.neptune.experiment_trackers.md#module-contents)
* [zenml.integrations.neptune.flavors package](zenml.integrations.neptune.flavors.md)
  * [Submodules](zenml.integrations.neptune.flavors.md#submodules)
  * [zenml.integrations.neptune.flavors.neptune_experiment_tracker_flavor module](zenml.integrations.neptune.flavors.md#zenml-integrations-neptune-flavors-neptune-experiment-tracker-flavor-module)
  * [Module contents](zenml.integrations.neptune.flavors.md#module-contents)

## Submodules

## zenml.integrations.neptune.neptune_constants module

Some constants for reading environment variables.

## Module contents

Module containing Neptune integration.

### *class* zenml.integrations.neptune.NeptuneIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of the neptune.ai integration with ZenML.

#### NAME *= 'neptune'*

#### REQUIREMENTS *: List[str]* *= ['neptune']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Neptune integration.

Returns:
: List of stack component flavors for this integration.
