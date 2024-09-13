# zenml.integrations.github package

## Subpackages

* [zenml.integrations.github.code_repositories package](zenml.integrations.github.code_repositories.md)
  * [Submodules](zenml.integrations.github.code_repositories.md#submodules)
  * [zenml.integrations.github.code_repositories.github_code_repository module](zenml.integrations.github.code_repositories.md#zenml-integrations-github-code-repositories-github-code-repository-module)
  * [Module contents](zenml.integrations.github.code_repositories.md#module-contents)
* [zenml.integrations.github.plugins package](zenml.integrations.github.plugins.md)
  * [Subpackages](zenml.integrations.github.plugins.md#subpackages)
    * [zenml.integrations.github.plugins.event_sources package](zenml.integrations.github.plugins.event_sources.md)
      * [Submodules](zenml.integrations.github.plugins.event_sources.md#submodules)
      * [zenml.integrations.github.plugins.event_sources.github_webhook_event_source module](zenml.integrations.github.plugins.event_sources.md#zenml-integrations-github-plugins-event-sources-github-webhook-event-source-module)
      * [Module contents](zenml.integrations.github.plugins.event_sources.md#module-contents)
  * [Submodules](zenml.integrations.github.plugins.md#submodules)
  * [zenml.integrations.github.plugins.github_webhook_event_source_flavor module](zenml.integrations.github.plugins.md#zenml-integrations-github-plugins-github-webhook-event-source-flavor-module)
  * [Module contents](zenml.integrations.github.plugins.md#module-contents)

## Module contents

Initialization of the GitHub ZenML integration.

### *class* zenml.integrations.github.GitHubIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of GitHub integration for ZenML.

#### NAME *= 'github'*

#### REQUIREMENTS *: List[str]* *= ['pygithub']*

#### *classmethod* plugin_flavors() → List[Type[[BasePluginFlavor](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]]

Declare the event flavors for the github integration.

Returns:
: List of stack component flavors for this integration.
