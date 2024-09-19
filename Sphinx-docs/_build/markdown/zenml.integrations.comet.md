# zenml.integrations.comet package

## Subpackages

* [zenml.integrations.comet.experiment_trackers package](zenml.integrations.comet.experiment_trackers.md)
  * [Submodules](zenml.integrations.comet.experiment_trackers.md#submodules)
  * [zenml.integrations.comet.experiment_trackers.comet_experiment_tracker module](zenml.integrations.comet.experiment_trackers.md#zenml-integrations-comet-experiment-trackers-comet-experiment-tracker-module)
  * [Module contents](zenml.integrations.comet.experiment_trackers.md#module-contents)
* [zenml.integrations.comet.flavors package](zenml.integrations.comet.flavors.md)
  * [Submodules](zenml.integrations.comet.flavors.md#submodules)
  * [zenml.integrations.comet.flavors.comet_experiment_tracker_flavor module](zenml.integrations.comet.flavors.md#zenml-integrations-comet-flavors-comet-experiment-tracker-flavor-module)
  * [Module contents](zenml.integrations.comet.flavors.md#module-contents)

## Module contents

Initialization for the Comet integration.

The CometML integrations currently enables you to use Comet tracking as a
convenient way to visualize your experiment runs within the Comet ui.

### *class* zenml.integrations.comet.CometIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Comet integration for ZenML.

#### NAME *= 'comet'*

#### REQUIREMENTS *: List[str]* *= ['comet-ml>=3.0.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Comet integration.

Returns:
: List of stack component flavors for this integration.
