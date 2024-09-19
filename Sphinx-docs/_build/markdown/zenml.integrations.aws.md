# zenml.integrations.aws package

## Subpackages

* [zenml.integrations.aws.container_registries package](zenml.integrations.aws.container_registries.md)
  * [Submodules](zenml.integrations.aws.container_registries.md#submodules)
  * [zenml.integrations.aws.container_registries.aws_container_registry module](zenml.integrations.aws.container_registries.md#zenml-integrations-aws-container-registries-aws-container-registry-module)
  * [Module contents](zenml.integrations.aws.container_registries.md#module-contents)
* [zenml.integrations.aws.flavors package](zenml.integrations.aws.flavors.md)
  * [Submodules](zenml.integrations.aws.flavors.md#submodules)
  * [zenml.integrations.aws.flavors.aws_container_registry_flavor module](zenml.integrations.aws.flavors.md#zenml-integrations-aws-flavors-aws-container-registry-flavor-module)
  * [zenml.integrations.aws.flavors.sagemaker_orchestrator_flavor module](zenml.integrations.aws.flavors.md#zenml-integrations-aws-flavors-sagemaker-orchestrator-flavor-module)
  * [zenml.integrations.aws.flavors.sagemaker_step_operator_flavor module](zenml.integrations.aws.flavors.md#zenml-integrations-aws-flavors-sagemaker-step-operator-flavor-module)
  * [Module contents](zenml.integrations.aws.flavors.md#module-contents)
* [zenml.integrations.aws.orchestrators package](zenml.integrations.aws.orchestrators.md)
  * [Submodules](zenml.integrations.aws.orchestrators.md#submodules)
  * [zenml.integrations.aws.orchestrators.sagemaker_orchestrator module](zenml.integrations.aws.orchestrators.md#zenml-integrations-aws-orchestrators-sagemaker-orchestrator-module)
  * [zenml.integrations.aws.orchestrators.sagemaker_orchestrator_entrypoint_config module](zenml.integrations.aws.orchestrators.md#zenml-integrations-aws-orchestrators-sagemaker-orchestrator-entrypoint-config-module)
  * [Module contents](zenml.integrations.aws.orchestrators.md#module-contents)
* [zenml.integrations.aws.service_connectors package](zenml.integrations.aws.service_connectors.md)
  * [Submodules](zenml.integrations.aws.service_connectors.md#submodules)
  * [zenml.integrations.aws.service_connectors.aws_service_connector module](zenml.integrations.aws.service_connectors.md#module-zenml.integrations.aws.service_connectors.aws_service_connector)
    * [`AWSAuthenticationMethods`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods)
      * [`AWSAuthenticationMethods.FEDERATION_TOKEN`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.FEDERATION_TOKEN)
      * [`AWSAuthenticationMethods.IAM_ROLE`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.IAM_ROLE)
      * [`AWSAuthenticationMethods.IMPLICIT`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.IMPLICIT)
      * [`AWSAuthenticationMethods.SECRET_KEY`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.SECRET_KEY)
      * [`AWSAuthenticationMethods.SESSION_TOKEN`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.SESSION_TOKEN)
      * [`AWSAuthenticationMethods.STS_TOKEN`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods.STS_TOKEN)
    * [`AWSBaseConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig)
      * [`AWSBaseConfig.endpoint_url`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig.endpoint_url)
      * [`AWSBaseConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig.model_computed_fields)
      * [`AWSBaseConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig.model_config)
      * [`AWSBaseConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig.model_fields)
      * [`AWSBaseConfig.region`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig.region)
    * [`AWSImplicitConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig)
      * [`AWSImplicitConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig.model_computed_fields)
      * [`AWSImplicitConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig.model_config)
      * [`AWSImplicitConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig.model_fields)
      * [`AWSImplicitConfig.profile_name`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig.profile_name)
      * [`AWSImplicitConfig.role_arn`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig.role_arn)
    * [`AWSSecretKey`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey)
      * [`AWSSecretKey.aws_access_key_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey.aws_access_key_id)
      * [`AWSSecretKey.aws_secret_access_key`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey.aws_secret_access_key)
      * [`AWSSecretKey.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey.model_computed_fields)
      * [`AWSSecretKey.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey.model_config)
      * [`AWSSecretKey.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey.model_fields)
    * [`AWSSecretKeyConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig)
      * [`AWSSecretKeyConfig.endpoint_url`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig.endpoint_url)
      * [`AWSSecretKeyConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig.model_computed_fields)
      * [`AWSSecretKeyConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig.model_config)
      * [`AWSSecretKeyConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig.model_fields)
      * [`AWSSecretKeyConfig.region`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig.region)
    * [`AWSServiceConnector`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector)
      * [`AWSServiceConnector.account_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.account_id)
      * [`AWSServiceConnector.config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.config)
      * [`AWSServiceConnector.get_boto3_session()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.get_boto3_session)
      * [`AWSServiceConnector.get_ecr_client()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.get_ecr_client)
      * [`AWSServiceConnector.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.model_computed_fields)
      * [`AWSServiceConnector.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.model_config)
      * [`AWSServiceConnector.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.model_fields)
      * [`AWSServiceConnector.model_post_init()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector.model_post_init)
    * [`AWSSessionPolicy`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy)
      * [`AWSSessionPolicy.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy.model_computed_fields)
      * [`AWSSessionPolicy.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy.model_config)
      * [`AWSSessionPolicy.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy.model_fields)
      * [`AWSSessionPolicy.policy`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy.policy)
      * [`AWSSessionPolicy.policy_arns`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy.policy_arns)
    * [`FederationTokenAuthenticationConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig)
      * [`FederationTokenAuthenticationConfig.aws_access_key_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.aws_access_key_id)
      * [`FederationTokenAuthenticationConfig.aws_secret_access_key`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.aws_secret_access_key)
      * [`FederationTokenAuthenticationConfig.endpoint_url`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.endpoint_url)
      * [`FederationTokenAuthenticationConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.model_computed_fields)
      * [`FederationTokenAuthenticationConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.model_config)
      * [`FederationTokenAuthenticationConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.model_fields)
      * [`FederationTokenAuthenticationConfig.region`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig.region)
    * [`IAMRoleAuthenticationConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig)
      * [`IAMRoleAuthenticationConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig.model_computed_fields)
      * [`IAMRoleAuthenticationConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig.model_config)
      * [`IAMRoleAuthenticationConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig.model_fields)
      * [`IAMRoleAuthenticationConfig.role_arn`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig.role_arn)
    * [`STSToken`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken)
      * [`STSToken.aws_session_token`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken.aws_session_token)
      * [`STSToken.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken.model_computed_fields)
      * [`STSToken.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken.model_config)
      * [`STSToken.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken.model_fields)
    * [`STSTokenConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig)
      * [`STSTokenConfig.endpoint_url`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig.endpoint_url)
      * [`STSTokenConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig.model_computed_fields)
      * [`STSTokenConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig.model_config)
      * [`STSTokenConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig.model_fields)
      * [`STSTokenConfig.region`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig.region)
    * [`SessionTokenAuthenticationConfig`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig)
      * [`SessionTokenAuthenticationConfig.aws_access_key_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.aws_access_key_id)
      * [`SessionTokenAuthenticationConfig.aws_secret_access_key`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.aws_secret_access_key)
      * [`SessionTokenAuthenticationConfig.endpoint_url`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.endpoint_url)
      * [`SessionTokenAuthenticationConfig.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.model_computed_fields)
      * [`SessionTokenAuthenticationConfig.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.model_config)
      * [`SessionTokenAuthenticationConfig.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.model_fields)
      * [`SessionTokenAuthenticationConfig.region`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig.region)
  * [Module contents](zenml.integrations.aws.service_connectors.md#module-zenml.integrations.aws.service_connectors)
    * [`AWSServiceConnector`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector)
      * [`AWSServiceConnector.account_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.account_id)
      * [`AWSServiceConnector.allow_implicit_auth_methods`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.allow_implicit_auth_methods)
      * [`AWSServiceConnector.auth_method`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.auth_method)
      * [`AWSServiceConnector.config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.config)
      * [`AWSServiceConnector.expiration_seconds`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.expiration_seconds)
      * [`AWSServiceConnector.expires_at`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.expires_at)
      * [`AWSServiceConnector.expires_skew_tolerance`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.expires_skew_tolerance)
      * [`AWSServiceConnector.get_boto3_session()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.get_boto3_session)
      * [`AWSServiceConnector.get_ecr_client()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.get_ecr_client)
      * [`AWSServiceConnector.id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.id)
      * [`AWSServiceConnector.model_computed_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.model_computed_fields)
      * [`AWSServiceConnector.model_config`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.model_config)
      * [`AWSServiceConnector.model_fields`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.model_fields)
      * [`AWSServiceConnector.model_post_init()`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.model_post_init)
      * [`AWSServiceConnector.name`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.name)
      * [`AWSServiceConnector.resource_id`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.resource_id)
      * [`AWSServiceConnector.resource_type`](zenml.integrations.aws.service_connectors.md#zenml.integrations.aws.service_connectors.AWSServiceConnector.resource_type)
* [zenml.integrations.aws.step_operators package](zenml.integrations.aws.step_operators.md)
  * [Submodules](zenml.integrations.aws.step_operators.md#submodules)
  * [zenml.integrations.aws.step_operators.sagemaker_step_operator module](zenml.integrations.aws.step_operators.md#zenml-integrations-aws-step-operators-sagemaker-step-operator-module)
  * [zenml.integrations.aws.step_operators.sagemaker_step_operator_entrypoint_config module](zenml.integrations.aws.step_operators.md#zenml-integrations-aws-step-operators-sagemaker-step-operator-entrypoint-config-module)
  * [Module contents](zenml.integrations.aws.step_operators.md#module-contents)

## Module contents

Integrates multiple AWS Tools as Stack Components.

The AWS integration provides a way for our users to manage their secrets
through AWS, a way to use the aws container registry. Additionally, the
Sagemaker integration submodule provides a way to run ZenML steps in
Sagemaker.

### *class* zenml.integrations.aws.AWSIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of AWS integration for ZenML.

#### NAME *= 'aws'*

#### REQUIREMENTS *: List[str]* *= ['sagemaker>=2.117.0', 'kubernetes', 'aws-profile-manager']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kubernetes']*

#### *classmethod* activate() → None

Activate the AWS integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the AWS integration.

Returns:
: List of stack component flavors for this integration.
