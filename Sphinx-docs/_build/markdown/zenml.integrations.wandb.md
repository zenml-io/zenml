# zenml.integrations.wandb package

## Subpackages

* [zenml.integrations.wandb.experiment_trackers package](zenml.integrations.wandb.experiment_trackers.md)
  * [Submodules](zenml.integrations.wandb.experiment_trackers.md#submodules)
  * [zenml.integrations.wandb.experiment_trackers.wandb_experiment_tracker module](zenml.integrations.wandb.experiment_trackers.md#zenml-integrations-wandb-experiment-trackers-wandb-experiment-tracker-module)
  * [Module contents](zenml.integrations.wandb.experiment_trackers.md#module-contents)
* [zenml.integrations.wandb.flavors package](zenml.integrations.wandb.flavors.md)
  * [Submodules](zenml.integrations.wandb.flavors.md#submodules)
  * [zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor module](zenml.integrations.wandb.flavors.md#zenml-integrations-wandb-flavors-wandb-experiment-tracker-flavor-module)
  * [Module contents](zenml.integrations.wandb.flavors.md#module-contents)

## Module contents

Initialization for the wandb integration.

The wandb integrations currently enables you to use wandb tracking as a
convenient way to visualize your experiment runs within the wandb ui.

### *class* zenml.integrations.wandb.WandbIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Plotly integration for ZenML.

#### NAME *= 'wandb'*

#### REQUIREMENTS *: List[str]* *= ['wandb>=0.12.12', 'Pillow>=9.1.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['Pillow']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Weights and Biases integration.

Returns:
: List of stack component flavors for this integration.
