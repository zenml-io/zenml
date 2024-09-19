# zenml.integrations.kubernetes package

## Subpackages

* [zenml.integrations.kubernetes.flavors package](zenml.integrations.kubernetes.flavors.md)
  * [Submodules](zenml.integrations.kubernetes.flavors.md#submodules)
  * [zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor module](zenml.integrations.kubernetes.flavors.md#zenml-integrations-kubernetes-flavors-kubernetes-orchestrator-flavor-module)
  * [zenml.integrations.kubernetes.flavors.kubernetes_step_operator_flavor module](zenml.integrations.kubernetes.flavors.md#zenml-integrations-kubernetes-flavors-kubernetes-step-operator-flavor-module)
  * [Module contents](zenml.integrations.kubernetes.flavors.md#module-contents)
* [zenml.integrations.kubernetes.orchestrators package](zenml.integrations.kubernetes.orchestrators.md)
  * [Submodules](zenml.integrations.kubernetes.orchestrators.md#submodules)
  * [zenml.integrations.kubernetes.orchestrators.kube_utils module](zenml.integrations.kubernetes.orchestrators.md#zenml-integrations-kubernetes-orchestrators-kube-utils-module)
  * [zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator module](zenml.integrations.kubernetes.orchestrators.md#zenml-integrations-kubernetes-orchestrators-kubernetes-orchestrator-module)
  * [zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint module](zenml.integrations.kubernetes.orchestrators.md#zenml-integrations-kubernetes-orchestrators-kubernetes-orchestrator-entrypoint-module)
  * [zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint_configuration module](zenml.integrations.kubernetes.orchestrators.md#zenml-integrations-kubernetes-orchestrators-kubernetes-orchestrator-entrypoint-configuration-module)
  * [zenml.integrations.kubernetes.orchestrators.manifest_utils module](zenml.integrations.kubernetes.orchestrators.md#zenml-integrations-kubernetes-orchestrators-manifest-utils-module)
  * [Module contents](zenml.integrations.kubernetes.orchestrators.md#module-contents)
* [zenml.integrations.kubernetes.service_connectors package](zenml.integrations.kubernetes.service_connectors.md)
  * [Submodules](zenml.integrations.kubernetes.service_connectors.md#submodules)
  * [zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector module](zenml.integrations.kubernetes.service_connectors.md#module-zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector)
    * [`KubernetesAuthenticationMethods`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesAuthenticationMethods)
      * [`KubernetesAuthenticationMethods.PASSWORD`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesAuthenticationMethods.PASSWORD)
      * [`KubernetesAuthenticationMethods.TOKEN`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesAuthenticationMethods.TOKEN)
    * [`KubernetesBaseConfig`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig)
      * [`KubernetesBaseConfig.cluster_name`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig.cluster_name)
      * [`KubernetesBaseConfig.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig.model_computed_fields)
      * [`KubernetesBaseConfig.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig.model_config)
      * [`KubernetesBaseConfig.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig.model_fields)
    * [`KubernetesServerConfig`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig)
      * [`KubernetesServerConfig.insecure`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig.insecure)
      * [`KubernetesServerConfig.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig.model_computed_fields)
      * [`KubernetesServerConfig.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig.model_config)
      * [`KubernetesServerConfig.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig.model_fields)
      * [`KubernetesServerConfig.server`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig.server)
    * [`KubernetesServerCredentials`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials)
      * [`KubernetesServerCredentials.certificate_authority`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials.certificate_authority)
      * [`KubernetesServerCredentials.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials.model_computed_fields)
      * [`KubernetesServerCredentials.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials.model_config)
      * [`KubernetesServerCredentials.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials.model_fields)
    * [`KubernetesServiceConnector`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector)
      * [`KubernetesServiceConnector.config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector.config)
      * [`KubernetesServiceConnector.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector.model_computed_fields)
      * [`KubernetesServiceConnector.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector.model_config)
      * [`KubernetesServiceConnector.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector.model_fields)
    * [`KubernetesTokenConfig`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig)
      * [`KubernetesTokenConfig.certificate_authority`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.certificate_authority)
      * [`KubernetesTokenConfig.cluster_name`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.cluster_name)
      * [`KubernetesTokenConfig.insecure`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.insecure)
      * [`KubernetesTokenConfig.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.model_computed_fields)
      * [`KubernetesTokenConfig.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.model_config)
      * [`KubernetesTokenConfig.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.model_fields)
      * [`KubernetesTokenConfig.server`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig.server)
    * [`KubernetesTokenCredentials`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials)
      * [`KubernetesTokenCredentials.client_certificate`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.client_certificate)
      * [`KubernetesTokenCredentials.client_key`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.client_key)
      * [`KubernetesTokenCredentials.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.model_computed_fields)
      * [`KubernetesTokenCredentials.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.model_config)
      * [`KubernetesTokenCredentials.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.model_fields)
      * [`KubernetesTokenCredentials.token`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials.token)
    * [`KubernetesUserPasswordConfig`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig)
      * [`KubernetesUserPasswordConfig.certificate_authority`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.certificate_authority)
      * [`KubernetesUserPasswordConfig.cluster_name`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.cluster_name)
      * [`KubernetesUserPasswordConfig.insecure`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.insecure)
      * [`KubernetesUserPasswordConfig.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.model_computed_fields)
      * [`KubernetesUserPasswordConfig.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.model_config)
      * [`KubernetesUserPasswordConfig.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.model_fields)
      * [`KubernetesUserPasswordConfig.server`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig.server)
    * [`KubernetesUserPasswordCredentials`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials)
      * [`KubernetesUserPasswordCredentials.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials.model_computed_fields)
      * [`KubernetesUserPasswordCredentials.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials.model_config)
      * [`KubernetesUserPasswordCredentials.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials.model_fields)
      * [`KubernetesUserPasswordCredentials.password`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials.password)
      * [`KubernetesUserPasswordCredentials.username`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials.username)
  * [Module contents](zenml.integrations.kubernetes.service_connectors.md#module-zenml.integrations.kubernetes.service_connectors)
    * [`KubernetesServiceConnector`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector)
      * [`KubernetesServiceConnector.allow_implicit_auth_methods`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.allow_implicit_auth_methods)
      * [`KubernetesServiceConnector.auth_method`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.auth_method)
      * [`KubernetesServiceConnector.config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.config)
      * [`KubernetesServiceConnector.expiration_seconds`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.expiration_seconds)
      * [`KubernetesServiceConnector.expires_at`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.expires_at)
      * [`KubernetesServiceConnector.expires_skew_tolerance`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.expires_skew_tolerance)
      * [`KubernetesServiceConnector.id`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.id)
      * [`KubernetesServiceConnector.model_computed_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.model_computed_fields)
      * [`KubernetesServiceConnector.model_config`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.model_config)
      * [`KubernetesServiceConnector.model_fields`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.model_fields)
      * [`KubernetesServiceConnector.name`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.name)
      * [`KubernetesServiceConnector.resource_id`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.resource_id)
      * [`KubernetesServiceConnector.resource_type`](zenml.integrations.kubernetes.service_connectors.md#zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector.resource_type)
* [zenml.integrations.kubernetes.step_operators package](zenml.integrations.kubernetes.step_operators.md)
  * [Submodules](zenml.integrations.kubernetes.step_operators.md#submodules)
  * [zenml.integrations.kubernetes.step_operators.kubernetes_step_operator module](zenml.integrations.kubernetes.step_operators.md#zenml-integrations-kubernetes-step-operators-kubernetes-step-operator-module)
  * [Module contents](zenml.integrations.kubernetes.step_operators.md#module-contents)

## Submodules

## zenml.integrations.kubernetes.pod_settings module

## zenml.integrations.kubernetes.serialization_utils module

Kubernetes serialization utils.

### zenml.integrations.kubernetes.serialization_utils.deserialize_kubernetes_model(data: Dict[str, Any], class_name: str) → Any

Deserializes a Kubernetes model.

Args:
: data: The model data.
  class_name: Name of the Kubernetes model class.

Raises:
: KeyError: If the data contains values for an invalid attribute.

Returns:
: The deserialized model.

### zenml.integrations.kubernetes.serialization_utils.get_model_class(class_name: str) → Type[Any]

Gets a Kubernetes model class.

Args:
: class_name: Name of the class to get.

Raises:
: TypeError: If no Kubernetes model class exists for this name.

Returns:
: The model class.

### zenml.integrations.kubernetes.serialization_utils.is_model_class(class_name: str) → bool

Checks whether the given class name is a Kubernetes model class.

Args:
: class_name: Name of the class to check.

Returns:
: If the given class name is a Kubernetes model class.

### zenml.integrations.kubernetes.serialization_utils.serialize_kubernetes_model(model: Any) → Dict[str, Any]

Serializes a Kubernetes model.

Args:
: model: The model to serialize.

Raises:
: TypeError: If the model is not a Kubernetes model.

Returns:
: The serialized model.

## Module contents

Kubernetes integration for Kubernetes-native orchestration.

The Kubernetes integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubernetes orchestrator with
the CLI tool.

### *class* zenml.integrations.kubernetes.KubernetesIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Kubernetes integration for ZenML.

#### NAME *= 'kubernetes'*

#### REQUIREMENTS *: List[str]* *= ['kubernetes>=21.7,<26']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kfp']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Kubernetes integration.

Returns:
: List of new stack component flavors.
