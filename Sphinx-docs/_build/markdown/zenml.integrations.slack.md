# zenml.integrations.slack package

## Subpackages

* [zenml.integrations.slack.alerters package](zenml.integrations.slack.alerters.md)
  * [Submodules](zenml.integrations.slack.alerters.md#submodules)
  * [zenml.integrations.slack.alerters.slack_alerter module](zenml.integrations.slack.alerters.md#zenml-integrations-slack-alerters-slack-alerter-module)
  * [Module contents](zenml.integrations.slack.alerters.md#module-contents)
* [zenml.integrations.slack.flavors package](zenml.integrations.slack.flavors.md)
  * [Submodules](zenml.integrations.slack.flavors.md#submodules)
  * [zenml.integrations.slack.flavors.slack_alerter_flavor module](zenml.integrations.slack.flavors.md#zenml-integrations-slack-flavors-slack-alerter-flavor-module)
  * [Module contents](zenml.integrations.slack.flavors.md#module-contents)
* [zenml.integrations.slack.steps package](zenml.integrations.slack.steps.md)
  * [Submodules](zenml.integrations.slack.steps.md#submodules)
  * [zenml.integrations.slack.steps.slack_alerter_ask_step module](zenml.integrations.slack.steps.md#zenml-integrations-slack-steps-slack-alerter-ask-step-module)
  * [zenml.integrations.slack.steps.slack_alerter_post_step module](zenml.integrations.slack.steps.md#zenml-integrations-slack-steps-slack-alerter-post-step-module)
  * [Module contents](zenml.integrations.slack.steps.md#module-zenml.integrations.slack.steps)

## Module contents

Slack integration for alerter components.

### *class* zenml.integrations.slack.SlackIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of a Slack integration for ZenML.

Implemented using [Slack SDK]([https://pypi.org/project/slack-sdk/](https://pypi.org/project/slack-sdk/)).

#### NAME *= 'slack'*

#### REQUIREMENTS *: List[str]* *= ['slack-sdk>=3.16.1', 'aiohttp>=3.8.1']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['aiohttp']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Slack integration.

Returns:
: List of new flavors defined by the Slack integration.
