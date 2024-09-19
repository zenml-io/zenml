# zenml.integrations.discord package

## Subpackages

* [zenml.integrations.discord.alerters package](zenml.integrations.discord.alerters.md)
  * [Submodules](zenml.integrations.discord.alerters.md#submodules)
  * [zenml.integrations.discord.alerters.discord_alerter module](zenml.integrations.discord.alerters.md#zenml-integrations-discord-alerters-discord-alerter-module)
  * [Module contents](zenml.integrations.discord.alerters.md#module-contents)
* [zenml.integrations.discord.flavors package](zenml.integrations.discord.flavors.md)
  * [Submodules](zenml.integrations.discord.flavors.md#submodules)
  * [zenml.integrations.discord.flavors.discord_alerter_flavor module](zenml.integrations.discord.flavors.md#zenml-integrations-discord-flavors-discord-alerter-flavor-module)
  * [Module contents](zenml.integrations.discord.flavors.md#module-contents)
* [zenml.integrations.discord.steps package](zenml.integrations.discord.steps.md)
  * [Submodules](zenml.integrations.discord.steps.md#submodules)
  * [zenml.integrations.discord.steps.discord_alerter_ask_step module](zenml.integrations.discord.steps.md#zenml-integrations-discord-steps-discord-alerter-ask-step-module)
  * [zenml.integrations.discord.steps.discord_alerter_post_step module](zenml.integrations.discord.steps.md#zenml-integrations-discord-steps-discord-alerter-post-step-module)
  * [Module contents](zenml.integrations.discord.steps.md#module-zenml.integrations.discord.steps)

## Module contents

Discord integration for alerter components.

### *class* zenml.integrations.discord.DiscordIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of a Discord integration for ZenML.

Implemented using [Discord API Wrapper]([https://pypi.org/project/discord.py/](https://pypi.org/project/discord.py/)).

#### NAME *= 'discord'*

#### REQUIREMENTS *: List[str]* *= ['discord.py>=2.3.2', 'aiohttp>=3.8.1', 'asyncio']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['aiohttp', 'asyncio']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Discord integration.

Returns:
: List of new flavors defined by the Discord integration.
