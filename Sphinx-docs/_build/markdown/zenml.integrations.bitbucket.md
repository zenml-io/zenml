# zenml.integrations.bitbucket package

## Subpackages

* [zenml.integrations.bitbucket.plugins package](zenml.integrations.bitbucket.plugins.md)
  * [Subpackages](zenml.integrations.bitbucket.plugins.md#subpackages)
    * [zenml.integrations.bitbucket.plugins.event_sources package](zenml.integrations.bitbucket.plugins.event_sources.md)
      * [Submodules](zenml.integrations.bitbucket.plugins.event_sources.md#submodules)
      * [zenml.integrations.bitbucket.plugins.event_sources.bitbucket_webhook_event_source module](zenml.integrations.bitbucket.plugins.event_sources.md#zenml-integrations-bitbucket-plugins-event-sources-bitbucket-webhook-event-source-module)
      * [Module contents](zenml.integrations.bitbucket.plugins.event_sources.md#module-contents)
  * [Submodules](zenml.integrations.bitbucket.plugins.md#submodules)
  * [zenml.integrations.bitbucket.plugins.bitbucket_webhook_event_source_flavor module](zenml.integrations.bitbucket.plugins.md#zenml-integrations-bitbucket-plugins-bitbucket-webhook-event-source-flavor-module)
  * [Module contents](zenml.integrations.bitbucket.plugins.md#module-contents)

## Module contents

Initialization of the bitbucket ZenML integration.

### *class* zenml.integrations.bitbucket.BitbucketIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of bitbucket integration for ZenML.

#### NAME *= 'bitbucket'*

#### REQUIREMENTS *: List[str]* *= []*

#### *classmethod* plugin_flavors() → List[Type[[BasePluginFlavor](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]]

Declare the event flavors for the bitbucket integration.

Returns:
: List of stack component flavors for this integration.
