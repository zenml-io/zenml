# zenml.integrations.azure package

## Subpackages

* [zenml.integrations.azure.artifact_stores package](zenml.integrations.azure.artifact_stores.md)
  * [Submodules](zenml.integrations.azure.artifact_stores.md#submodules)
  * [zenml.integrations.azure.artifact_stores.azure_artifact_store module](zenml.integrations.azure.artifact_stores.md#zenml-integrations-azure-artifact-stores-azure-artifact-store-module)
  * [Module contents](zenml.integrations.azure.artifact_stores.md#module-contents)
* [zenml.integrations.azure.flavors package](zenml.integrations.azure.flavors.md)
  * [Submodules](zenml.integrations.azure.flavors.md#submodules)
  * [zenml.integrations.azure.flavors.azure_artifact_store_flavor module](zenml.integrations.azure.flavors.md#zenml-integrations-azure-flavors-azure-artifact-store-flavor-module)
  * [zenml.integrations.azure.flavors.azureml module](zenml.integrations.azure.flavors.md#zenml-integrations-azure-flavors-azureml-module)
  * [zenml.integrations.azure.flavors.azureml_orchestrator_flavor module](zenml.integrations.azure.flavors.md#zenml-integrations-azure-flavors-azureml-orchestrator-flavor-module)
  * [zenml.integrations.azure.flavors.azureml_step_operator_flavor module](zenml.integrations.azure.flavors.md#zenml-integrations-azure-flavors-azureml-step-operator-flavor-module)
  * [Module contents](zenml.integrations.azure.flavors.md#module-contents)
* [zenml.integrations.azure.orchestrators package](zenml.integrations.azure.orchestrators.md)
  * [Submodules](zenml.integrations.azure.orchestrators.md#submodules)
  * [zenml.integrations.azure.orchestrators.azureml_orchestrator module](zenml.integrations.azure.orchestrators.md#zenml-integrations-azure-orchestrators-azureml-orchestrator-module)
  * [zenml.integrations.azure.orchestrators.azureml_orchestrator_entrypoint_config module](zenml.integrations.azure.orchestrators.md#zenml-integrations-azure-orchestrators-azureml-orchestrator-entrypoint-config-module)
  * [Module contents](zenml.integrations.azure.orchestrators.md#module-contents)
* [zenml.integrations.azure.service_connectors package](zenml.integrations.azure.service_connectors.md)
  * [Submodules](zenml.integrations.azure.service_connectors.md#submodules)
  * [zenml.integrations.azure.service_connectors.azure_service_connector module](zenml.integrations.azure.service_connectors.md#module-zenml.integrations.azure.service_connectors.azure_service_connector)
    * [`AzureAccessToken`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken)
      * [`AzureAccessToken.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken.model_computed_fields)
      * [`AzureAccessToken.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken.model_config)
      * [`AzureAccessToken.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken.model_fields)
      * [`AzureAccessToken.token`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken.token)
    * [`AzureAccessTokenConfig`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig)
      * [`AzureAccessTokenConfig.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.model_computed_fields)
      * [`AzureAccessTokenConfig.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.model_config)
      * [`AzureAccessTokenConfig.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.model_fields)
      * [`AzureAccessTokenConfig.resource_group`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.resource_group)
      * [`AzureAccessTokenConfig.storage_account`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.storage_account)
      * [`AzureAccessTokenConfig.subscription_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.subscription_id)
      * [`AzureAccessTokenConfig.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig.tenant_id)
    * [`AzureAuthenticationMethods`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAuthenticationMethods)
      * [`AzureAuthenticationMethods.ACCESS_TOKEN`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAuthenticationMethods.ACCESS_TOKEN)
      * [`AzureAuthenticationMethods.IMPLICIT`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAuthenticationMethods.IMPLICIT)
      * [`AzureAuthenticationMethods.SERVICE_PRINCIPAL`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAuthenticationMethods.SERVICE_PRINCIPAL)
    * [`AzureBaseConfig`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig)
      * [`AzureBaseConfig.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.model_computed_fields)
      * [`AzureBaseConfig.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.model_config)
      * [`AzureBaseConfig.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.model_fields)
      * [`AzureBaseConfig.resource_group`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.resource_group)
      * [`AzureBaseConfig.storage_account`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.storage_account)
      * [`AzureBaseConfig.subscription_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.subscription_id)
      * [`AzureBaseConfig.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig.tenant_id)
    * [`AzureClientConfig`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig)
      * [`AzureClientConfig.client_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig.client_id)
      * [`AzureClientConfig.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig.model_computed_fields)
      * [`AzureClientConfig.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig.model_config)
      * [`AzureClientConfig.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig.model_fields)
      * [`AzureClientConfig.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig.tenant_id)
    * [`AzureClientSecret`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret)
      * [`AzureClientSecret.client_secret`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret.client_secret)
      * [`AzureClientSecret.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret.model_computed_fields)
      * [`AzureClientSecret.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret.model_config)
      * [`AzureClientSecret.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret.model_fields)
    * [`AzureServiceConnector`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector)
      * [`AzureServiceConnector.config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.config)
      * [`AzureServiceConnector.get_azure_credential()`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.get_azure_credential)
      * [`AzureServiceConnector.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.model_computed_fields)
      * [`AzureServiceConnector.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.model_config)
      * [`AzureServiceConnector.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.model_fields)
      * [`AzureServiceConnector.model_post_init()`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.model_post_init)
      * [`AzureServiceConnector.subscription`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.subscription)
      * [`AzureServiceConnector.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector.tenant_id)
    * [`AzureServicePrincipalConfig`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig)
      * [`AzureServicePrincipalConfig.client_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.client_id)
      * [`AzureServicePrincipalConfig.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.model_computed_fields)
      * [`AzureServicePrincipalConfig.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.model_config)
      * [`AzureServicePrincipalConfig.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.model_fields)
      * [`AzureServicePrincipalConfig.resource_group`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.resource_group)
      * [`AzureServicePrincipalConfig.storage_account`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.storage_account)
      * [`AzureServicePrincipalConfig.subscription_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.subscription_id)
      * [`AzureServicePrincipalConfig.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig.tenant_id)
    * [`ZenMLAzureTokenCredential`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.ZenMLAzureTokenCredential)
      * [`ZenMLAzureTokenCredential.get_token()`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.azure_service_connector.ZenMLAzureTokenCredential.get_token)
  * [Module contents](zenml.integrations.azure.service_connectors.md#module-zenml.integrations.azure.service_connectors)
    * [`AzureServiceConnector`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector)
      * [`AzureServiceConnector.allow_implicit_auth_methods`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.allow_implicit_auth_methods)
      * [`AzureServiceConnector.auth_method`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.auth_method)
      * [`AzureServiceConnector.config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.config)
      * [`AzureServiceConnector.expiration_seconds`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.expiration_seconds)
      * [`AzureServiceConnector.expires_at`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.expires_at)
      * [`AzureServiceConnector.expires_skew_tolerance`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.expires_skew_tolerance)
      * [`AzureServiceConnector.get_azure_credential()`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.get_azure_credential)
      * [`AzureServiceConnector.id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.id)
      * [`AzureServiceConnector.model_computed_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.model_computed_fields)
      * [`AzureServiceConnector.model_config`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.model_config)
      * [`AzureServiceConnector.model_fields`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.model_fields)
      * [`AzureServiceConnector.model_post_init()`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.model_post_init)
      * [`AzureServiceConnector.name`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.name)
      * [`AzureServiceConnector.resource_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.resource_id)
      * [`AzureServiceConnector.resource_type`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.resource_type)
      * [`AzureServiceConnector.subscription`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.subscription)
      * [`AzureServiceConnector.tenant_id`](zenml.integrations.azure.service_connectors.md#zenml.integrations.azure.service_connectors.AzureServiceConnector.tenant_id)
* [zenml.integrations.azure.step_operators package](zenml.integrations.azure.step_operators.md)
  * [Submodules](zenml.integrations.azure.step_operators.md#submodules)
  * [zenml.integrations.azure.step_operators.azureml_step_operator module](zenml.integrations.azure.step_operators.md#zenml-integrations-azure-step-operators-azureml-step-operator-module)
  * [Module contents](zenml.integrations.azure.step_operators.md#module-contents)

## Submodules

## zenml.integrations.azure.azureml_utils module

## Module contents

Initialization of the ZenML Azure integration.

The Azure integration submodule provides a way to run ZenML pipelines in a cloud
environment. Specifically, it allows the use of cloud artifact stores,
and an io module to handle file operations on Azure Blob Storage.
The Azure Step Operator integration submodule provides a way to run ZenML steps
in AzureML.

### *class* zenml.integrations.azure.AzureIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Azure integration for ZenML.

#### NAME *= 'azure'*

#### REQUIREMENTS *: List[str]* *= ['adlfs>=2021.10.0', 'azure-keyvault-keys', 'azure-keyvault-secrets', 'azure-identity', 'azureml-core==1.56.0', 'azure-mgmt-containerservice>=20.0.0', 'azure-storage-blob==12.17.0', 'kubernetes', 'azure-ai-ml==1.18.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kubernetes']*

#### *classmethod* activate() → None

Activate the Azure integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declares the flavors for the integration.

Returns:
: List of stack component flavors for this integration.
