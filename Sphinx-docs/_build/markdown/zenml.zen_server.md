# zenml.zen_server package

## Subpackages

* [zenml.zen_server.deploy package](zenml.zen_server.deploy.md)
  * [Subpackages](zenml.zen_server.deploy.md#subpackages)
    * [zenml.zen_server.deploy.docker package](zenml.zen_server.deploy.docker.md)
      * [Submodules](zenml.zen_server.deploy.docker.md#submodules)
      * [zenml.zen_server.deploy.docker.docker_provider module](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker.docker_provider)
      * [zenml.zen_server.deploy.docker.docker_zen_server module](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker.docker_zen_server)
      * [Module contents](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker)
    * [zenml.zen_server.deploy.local package](zenml.zen_server.deploy.local.md)
      * [Submodules](zenml.zen_server.deploy.local.md#submodules)
      * [zenml.zen_server.deploy.local.local_provider module](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local.local_provider)
      * [zenml.zen_server.deploy.local.local_zen_server module](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local.local_zen_server)
      * [Module contents](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local)
    * [zenml.zen_server.deploy.terraform package](zenml.zen_server.deploy.terraform.md)
      * [Subpackages](zenml.zen_server.deploy.terraform.md#subpackages)
      * [Submodules](zenml.zen_server.deploy.terraform.md#submodules)
      * [zenml.zen_server.deploy.terraform.terraform_zen_server module](zenml.zen_server.deploy.terraform.md#zenml-zen-server-deploy-terraform-terraform-zen-server-module)
      * [Module contents](zenml.zen_server.deploy.terraform.md#module-contents)
  * [Submodules](zenml.zen_server.deploy.md#submodules)
  * [zenml.zen_server.deploy.base_provider module](zenml.zen_server.deploy.md#module-zenml.zen_server.deploy.base_provider)
    * [`BaseServerProvider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider)
      * [`BaseServerProvider.CONFIG_TYPE`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.CONFIG_TYPE)
      * [`BaseServerProvider.TYPE`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.TYPE)
      * [`BaseServerProvider.deploy_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.deploy_server)
      * [`BaseServerProvider.get_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.get_server)
      * [`BaseServerProvider.get_server_logs()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.get_server_logs)
      * [`BaseServerProvider.list_servers()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.list_servers)
      * [`BaseServerProvider.register_as_provider()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.register_as_provider)
      * [`BaseServerProvider.remove_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.remove_server)
      * [`BaseServerProvider.update_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider.update_server)
  * [zenml.zen_server.deploy.deployer module](zenml.zen_server.deploy.md#module-zenml.zen_server.deploy.deployer)
    * [`ServerDeployer`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer)
      * [`ServerDeployer.connect_to_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.connect_to_server)
      * [`ServerDeployer.deploy_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.deploy_server)
      * [`ServerDeployer.disconnect_from_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.disconnect_from_server)
      * [`ServerDeployer.get_provider()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.get_provider)
      * [`ServerDeployer.get_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.get_server)
      * [`ServerDeployer.get_server_logs()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.get_server_logs)
      * [`ServerDeployer.is_connected_to_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.is_connected_to_server)
      * [`ServerDeployer.list_servers()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.list_servers)
      * [`ServerDeployer.register_provider()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.register_provider)
      * [`ServerDeployer.remove_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.remove_server)
      * [`ServerDeployer.update_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployer.ServerDeployer.update_server)
  * [zenml.zen_server.deploy.deployment module](zenml.zen_server.deploy.md#module-zenml.zen_server.deploy.deployment)
    * [`ServerDeployment`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment)
      * [`ServerDeployment.config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.config)
      * [`ServerDeployment.is_running`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.is_running)
      * [`ServerDeployment.model_computed_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.model_computed_fields)
      * [`ServerDeployment.model_config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.model_config)
      * [`ServerDeployment.model_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.model_fields)
      * [`ServerDeployment.status`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment.status)
    * [`ServerDeploymentConfig`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)
      * [`ServerDeploymentConfig.model_computed_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig.model_computed_fields)
      * [`ServerDeploymentConfig.model_config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig.model_config)
      * [`ServerDeploymentConfig.model_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig.model_fields)
      * [`ServerDeploymentConfig.name`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig.name)
      * [`ServerDeploymentConfig.provider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig.provider)
    * [`ServerDeploymentStatus`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus)
      * [`ServerDeploymentStatus.ca_crt`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.ca_crt)
      * [`ServerDeploymentStatus.connected`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.connected)
      * [`ServerDeploymentStatus.model_computed_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.model_computed_fields)
      * [`ServerDeploymentStatus.model_config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.model_config)
      * [`ServerDeploymentStatus.model_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.model_fields)
      * [`ServerDeploymentStatus.status`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.status)
      * [`ServerDeploymentStatus.status_message`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.status_message)
      * [`ServerDeploymentStatus.url`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentStatus.url)
  * [zenml.zen_server.deploy.exceptions module](zenml.zen_server.deploy.md#module-zenml.zen_server.deploy.exceptions)
    * [`ServerDeploymentConfigurationError`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.exceptions.ServerDeploymentConfigurationError)
    * [`ServerDeploymentError`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.exceptions.ServerDeploymentError)
    * [`ServerDeploymentExistsError`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.exceptions.ServerDeploymentExistsError)
    * [`ServerDeploymentNotFoundError`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.exceptions.ServerDeploymentNotFoundError)
    * [`ServerProviderNotFoundError`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.exceptions.ServerProviderNotFoundError)
  * [Module contents](zenml.zen_server.deploy.md#module-zenml.zen_server.deploy)
    * [`ServerDeployer`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer)
      * [`ServerDeployer.connect_to_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.connect_to_server)
      * [`ServerDeployer.deploy_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.deploy_server)
      * [`ServerDeployer.disconnect_from_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.disconnect_from_server)
      * [`ServerDeployer.get_provider()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.get_provider)
      * [`ServerDeployer.get_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.get_server)
      * [`ServerDeployer.get_server_logs()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.get_server_logs)
      * [`ServerDeployer.is_connected_to_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.is_connected_to_server)
      * [`ServerDeployer.list_servers()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.list_servers)
      * [`ServerDeployer.register_provider()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.register_provider)
      * [`ServerDeployer.remove_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.remove_server)
      * [`ServerDeployer.update_server()`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployer.update_server)
    * [`ServerDeployment`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment)
      * [`ServerDeployment.config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.config)
      * [`ServerDeployment.is_running`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.is_running)
      * [`ServerDeployment.model_computed_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.model_computed_fields)
      * [`ServerDeployment.model_config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.model_config)
      * [`ServerDeployment.model_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.model_fields)
      * [`ServerDeployment.status`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeployment.status)
    * [`ServerDeploymentConfig`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig)
      * [`ServerDeploymentConfig.model_computed_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig.model_computed_fields)
      * [`ServerDeploymentConfig.model_config`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig.model_config)
      * [`ServerDeploymentConfig.model_fields`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig.model_fields)
      * [`ServerDeploymentConfig.name`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig.name)
      * [`ServerDeploymentConfig.provider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.ServerDeploymentConfig.provider)
* [zenml.zen_server.feature_gate package](zenml.zen_server.feature_gate.md)
  * [Submodules](zenml.zen_server.feature_gate.md#submodules)
  * [zenml.zen_server.feature_gate.endpoint_utils module](zenml.zen_server.feature_gate.md#module-zenml.zen_server.feature_gate.endpoint_utils)
    * [`check_entitlement()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.endpoint_utils.check_entitlement)
    * [`report_decrement()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.endpoint_utils.report_decrement)
    * [`report_usage()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.endpoint_utils.report_usage)
  * [zenml.zen_server.feature_gate.feature_gate_interface module](zenml.zen_server.feature_gate.md#module-zenml.zen_server.feature_gate.feature_gate_interface)
    * [`FeatureGateInterface`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface)
      * [`FeatureGateInterface.check_entitlement()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface.check_entitlement)
      * [`FeatureGateInterface.report_event()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface.report_event)
  * [zenml.zen_server.feature_gate.zenml_cloud_feature_gate module](zenml.zen_server.feature_gate.md#module-zenml.zen_server.feature_gate.zenml_cloud_feature_gate)
    * [`RawUsageEvent`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent)
      * [`RawUsageEvent.feature`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.feature)
      * [`RawUsageEvent.metadata`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.metadata)
      * [`RawUsageEvent.model_computed_fields`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.model_computed_fields)
      * [`RawUsageEvent.model_config`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.model_config)
      * [`RawUsageEvent.model_fields`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.model_fields)
      * [`RawUsageEvent.organization_id`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.organization_id)
      * [`RawUsageEvent.total`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent.total)
    * [`ZenMLCloudFeatureGateInterface`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.ZenMLCloudFeatureGateInterface)
      * [`ZenMLCloudFeatureGateInterface.check_entitlement()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.ZenMLCloudFeatureGateInterface.check_entitlement)
      * [`ZenMLCloudFeatureGateInterface.report_event()`](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.zenml_cloud_feature_gate.ZenMLCloudFeatureGateInterface.report_event)
  * [Module contents](zenml.zen_server.feature_gate.md#module-zenml.zen_server.feature_gate)
* [zenml.zen_server.rbac package](zenml.zen_server.rbac.md)
  * [Submodules](zenml.zen_server.rbac.md#submodules)
  * [zenml.zen_server.rbac.endpoint_utils module](zenml.zen_server.rbac.md#zenml-zen-server-rbac-endpoint-utils-module)
  * [zenml.zen_server.rbac.models module](zenml.zen_server.rbac.md#module-zenml.zen_server.rbac.models)
    * [`Action`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action)
      * [`Action.BACKUP_RESTORE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.BACKUP_RESTORE)
      * [`Action.CLIENT`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.CLIENT)
      * [`Action.CREATE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.CREATE)
      * [`Action.DELETE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.DELETE)
      * [`Action.PROMOTE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.PROMOTE)
      * [`Action.PRUNE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.PRUNE)
      * [`Action.READ`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.READ)
      * [`Action.READ_SECRET_VALUE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.READ_SECRET_VALUE)
      * [`Action.SHARE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.SHARE)
      * [`Action.UPDATE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Action.UPDATE)
    * [`Resource`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource)
      * [`Resource.id`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource.id)
      * [`Resource.model_computed_fields`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource.model_computed_fields)
      * [`Resource.model_config`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource.model_config)
      * [`Resource.model_fields`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource.model_fields)
      * [`Resource.type`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.Resource.type)
    * [`ResourceType`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType)
      * [`ResourceType.ACTION`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.ACTION)
      * [`ResourceType.ARTIFACT`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.ARTIFACT)
      * [`ResourceType.ARTIFACT_VERSION`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.ARTIFACT_VERSION)
      * [`ResourceType.CODE_REPOSITORY`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.CODE_REPOSITORY)
      * [`ResourceType.EVENT_SOURCE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.EVENT_SOURCE)
      * [`ResourceType.FLAVOR`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.FLAVOR)
      * [`ResourceType.MODEL`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.MODEL)
      * [`ResourceType.MODEL_VERSION`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.MODEL_VERSION)
      * [`ResourceType.PIPELINE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.PIPELINE)
      * [`ResourceType.PIPELINE_BUILD`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.PIPELINE_BUILD)
      * [`ResourceType.PIPELINE_DEPLOYMENT`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.PIPELINE_DEPLOYMENT)
      * [`ResourceType.PIPELINE_RUN`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.PIPELINE_RUN)
      * [`ResourceType.RUN_METADATA`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.RUN_METADATA)
      * [`ResourceType.RUN_TEMPLATE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.RUN_TEMPLATE)
      * [`ResourceType.SECRET`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.SECRET)
      * [`ResourceType.SERVICE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.SERVICE)
      * [`ResourceType.SERVICE_ACCOUNT`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.SERVICE_ACCOUNT)
      * [`ResourceType.SERVICE_CONNECTOR`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.SERVICE_CONNECTOR)
      * [`ResourceType.STACK`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.STACK)
      * [`ResourceType.STACK_COMPONENT`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.STACK_COMPONENT)
      * [`ResourceType.TAG`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.TAG)
      * [`ResourceType.TRIGGER`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.TRIGGER)
      * [`ResourceType.TRIGGER_EXECUTION`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.TRIGGER_EXECUTION)
      * [`ResourceType.USER`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.USER)
      * [`ResourceType.WORKSPACE`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType.WORKSPACE)
  * [zenml.zen_server.rbac.rbac_interface module](zenml.zen_server.rbac.md#module-zenml.zen_server.rbac.rbac_interface)
    * [`RBACInterface`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.rbac_interface.RBACInterface)
      * [`RBACInterface.check_permissions()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.rbac_interface.RBACInterface.check_permissions)
      * [`RBACInterface.list_allowed_resource_ids()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.rbac_interface.RBACInterface.list_allowed_resource_ids)
      * [`RBACInterface.update_resource_membership()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.rbac_interface.RBACInterface.update_resource_membership)
  * [zenml.zen_server.rbac.utils module](zenml.zen_server.rbac.md#zenml-zen-server-rbac-utils-module)
  * [zenml.zen_server.rbac.zenml_cloud_rbac module](zenml.zen_server.rbac.md#module-zenml.zen_server.rbac.zenml_cloud_rbac)
    * [`ZenMLCloudRBAC`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.zenml_cloud_rbac.ZenMLCloudRBAC)
      * [`ZenMLCloudRBAC.check_permissions()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.zenml_cloud_rbac.ZenMLCloudRBAC.check_permissions)
      * [`ZenMLCloudRBAC.list_allowed_resource_ids()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.zenml_cloud_rbac.ZenMLCloudRBAC.list_allowed_resource_ids)
      * [`ZenMLCloudRBAC.update_resource_membership()`](zenml.zen_server.rbac.md#zenml.zen_server.rbac.zenml_cloud_rbac.ZenMLCloudRBAC.update_resource_membership)
  * [Module contents](zenml.zen_server.rbac.md#module-zenml.zen_server.rbac)
* [zenml.zen_server.routers package](zenml.zen_server.routers.md)
  * [Submodules](zenml.zen_server.routers.md#submodules)
  * [zenml.zen_server.routers.actions_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-actions-endpoints-module)
  * [zenml.zen_server.routers.artifact_endpoint module](zenml.zen_server.routers.md#zenml-zen-server-routers-artifact-endpoint-module)
  * [zenml.zen_server.routers.artifact_version_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-artifact-version-endpoints-module)
  * [zenml.zen_server.routers.auth_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-auth-endpoints-module)
  * [zenml.zen_server.routers.code_repositories_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-code-repositories-endpoints-module)
  * [zenml.zen_server.routers.devices_endpoints module](zenml.zen_server.routers.md#module-zenml.zen_server.routers.devices_endpoints)
    * [`delete_authorized_device()`](zenml.zen_server.routers.md#zenml.zen_server.routers.devices_endpoints.delete_authorized_device)
    * [`get_authorization_device()`](zenml.zen_server.routers.md#zenml.zen_server.routers.devices_endpoints.get_authorization_device)
    * [`list_authorized_devices()`](zenml.zen_server.routers.md#zenml.zen_server.routers.devices_endpoints.list_authorized_devices)
    * [`update_authorized_device()`](zenml.zen_server.routers.md#zenml.zen_server.routers.devices_endpoints.update_authorized_device)
    * [`verify_authorized_device()`](zenml.zen_server.routers.md#zenml.zen_server.routers.devices_endpoints.verify_authorized_device)
  * [zenml.zen_server.routers.event_source_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-event-source-endpoints-module)
  * [zenml.zen_server.routers.flavors_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-flavors-endpoints-module)
  * [zenml.zen_server.routers.model_versions_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-model-versions-endpoints-module)
  * [zenml.zen_server.routers.models_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-models-endpoints-module)
  * [zenml.zen_server.routers.pipeline_builds_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-pipeline-builds-endpoints-module)
  * [zenml.zen_server.routers.pipeline_deployments_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-pipeline-deployments-endpoints-module)
  * [zenml.zen_server.routers.pipelines_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-pipelines-endpoints-module)
  * [zenml.zen_server.routers.plugin_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-plugin-endpoints-module)
  * [zenml.zen_server.routers.run_metadata_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-run-metadata-endpoints-module)
  * [zenml.zen_server.routers.run_templates_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-run-templates-endpoints-module)
  * [zenml.zen_server.routers.runs_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-runs-endpoints-module)
  * [zenml.zen_server.routers.schedule_endpoints module](zenml.zen_server.routers.md#module-zenml.zen_server.routers.schedule_endpoints)
    * [`delete_schedule()`](zenml.zen_server.routers.md#zenml.zen_server.routers.schedule_endpoints.delete_schedule)
    * [`get_schedule()`](zenml.zen_server.routers.md#zenml.zen_server.routers.schedule_endpoints.get_schedule)
    * [`list_schedules()`](zenml.zen_server.routers.md#zenml.zen_server.routers.schedule_endpoints.list_schedules)
    * [`update_schedule()`](zenml.zen_server.routers.md#zenml.zen_server.routers.schedule_endpoints.update_schedule)
  * [zenml.zen_server.routers.secrets_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-secrets-endpoints-module)
  * [zenml.zen_server.routers.server_endpoints module](zenml.zen_server.routers.md#module-zenml.zen_server.routers.server_endpoints)
    * [`activate_server()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.activate_server)
    * [`get_onboarding_state()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.get_onboarding_state)
    * [`get_settings()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.get_settings)
    * [`server_info()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.server_info)
    * [`update_server_settings()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.update_server_settings)
    * [`version()`](zenml.zen_server.routers.md#zenml.zen_server.routers.server_endpoints.version)
  * [zenml.zen_server.routers.service_accounts_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-service-accounts-endpoints-module)
  * [zenml.zen_server.routers.service_connectors_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-service-connectors-endpoints-module)
  * [zenml.zen_server.routers.service_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-service-endpoints-module)
  * [zenml.zen_server.routers.stack_components_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-stack-components-endpoints-module)
  * [zenml.zen_server.routers.stack_deployment_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-stack-deployment-endpoints-module)
  * [zenml.zen_server.routers.stacks_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-stacks-endpoints-module)
  * [zenml.zen_server.routers.steps_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-steps-endpoints-module)
  * [zenml.zen_server.routers.tags_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-tags-endpoints-module)
  * [zenml.zen_server.routers.triggers_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-triggers-endpoints-module)
  * [zenml.zen_server.routers.users_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-users-endpoints-module)
  * [zenml.zen_server.routers.webhook_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-webhook-endpoints-module)
  * [zenml.zen_server.routers.workspaces_endpoints module](zenml.zen_server.routers.md#zenml-zen-server-routers-workspaces-endpoints-module)
  * [Module contents](zenml.zen_server.routers.md#module-zenml.zen_server.routers)
* [zenml.zen_server.template_execution package](zenml.zen_server.template_execution.md)
  * [Submodules](zenml.zen_server.template_execution.md#submodules)
  * [zenml.zen_server.template_execution.runner_entrypoint_configuration module](zenml.zen_server.template_execution.md#module-zenml.zen_server.template_execution.runner_entrypoint_configuration)
    * [`RunnerEntrypointConfiguration`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.runner_entrypoint_configuration.RunnerEntrypointConfiguration)
      * [`RunnerEntrypointConfiguration.run()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.runner_entrypoint_configuration.RunnerEntrypointConfiguration.run)
  * [zenml.zen_server.template_execution.utils module](zenml.zen_server.template_execution.md#module-zenml.zen_server.template_execution.utils)
    * [`deployment_request_from_template()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.deployment_request_from_template)
    * [`ensure_async_orchestrator()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.ensure_async_orchestrator)
    * [`generate_dockerfile()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.generate_dockerfile)
    * [`generate_image_hash()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.generate_image_hash)
    * [`get_pipeline_run_analytics_metadata()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.get_pipeline_run_analytics_metadata)
    * [`get_requirements_for_component()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.get_requirements_for_component)
    * [`get_requirements_for_stack()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.get_requirements_for_stack)
    * [`run_template()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.utils.run_template)
  * [zenml.zen_server.template_execution.workload_manager_interface module](zenml.zen_server.template_execution.md#module-zenml.zen_server.template_execution.workload_manager_interface)
    * [`WorkloadManagerInterface`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface)
      * [`WorkloadManagerInterface.build_and_push_image()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface.build_and_push_image)
      * [`WorkloadManagerInterface.delete_workload()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface.delete_workload)
      * [`WorkloadManagerInterface.get_logs()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface.get_logs)
      * [`WorkloadManagerInterface.log()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface.log)
      * [`WorkloadManagerInterface.run()`](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface.run)
  * [Module contents](zenml.zen_server.template_execution.md#module-zenml.zen_server.template_execution)

## Submodules

## zenml.zen_server.auth module

Authentication module for ZenML server.

### *class* zenml.zen_server.auth.AuthContext(\*, user: [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse), access_token: [JWTToken](#zenml.zen_server.jwt.JWTToken) | None = None, encoded_access_token: str | None = None, device: [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse) | None = None, api_key: [APIKeyInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalResponse) | None = None)

Bases: `BaseModel`

The authentication context.

#### access_token *: [JWTToken](#zenml.zen_server.jwt.JWTToken) | None*

#### api_key *: [APIKeyInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalResponse) | None*

#### device *: [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse) | None*

#### encoded_access_token *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'access_token': FieldInfo(annotation=Union[JWTToken, NoneType], required=False, default=None), 'api_key': FieldInfo(annotation=Union[APIKeyInternalResponse, NoneType], required=False, default=None), 'device': FieldInfo(annotation=Union[OAuthDeviceInternalResponse, NoneType], required=False, default=None), 'encoded_access_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'user': FieldInfo(annotation=UserResponse, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user *: [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)*

### *class* zenml.zen_server.auth.CookieOAuth2TokenBearer(tokenUrl: Annotated[str, Doc('\\n                The URL to obtain the OAuth2 token. This would be the \*path operation\*\\n                that has \`OAuth2PasswordRequestForm\` as a dependency.\\n                ')], scheme_name: Annotated[str | None, Doc('\\n                Security scheme name.\\n\\n                It will be included in the generated OpenAPI (e.g. visible at \`/docs\`).\\n                ')] = None, scopes: Annotated[Dict[str, str] | None, Doc('\\n                The OAuth2 scopes that would be required by the \*path operations\* that\\n                use this dependency.\\n                ')] = None, description: Annotated[str | None, Doc('\\n                Security scheme description.\\n\\n                It will be included in the generated OpenAPI (e.g. visible at \`/docs\`).\\n                ')] = None, auto_error: Annotated[bool, Doc('\\n                By default, if no HTTP Auhtorization header is provided, required for\\n                OAuth2 authentication, it will automatically cancel the request and\\n                send the client an error.\\n\\n                If \`auto_error\` is set to \`False\`, when the HTTP Authorization header\\n                is not available, instead of erroring out, the dependency result will\\n                be \`None\`.\\n\\n                This is useful when you want to have optional authentication.\\n\\n                It is also useful when you want to have authentication that can be\\n                provided in one of multiple optional ways (for example, with OAuth2\\n                or in a cookie).\\n                ')] = True)

Bases: `OAuth2PasswordBearer`

OAuth2 token bearer authentication scheme that uses a cookie.

### zenml.zen_server.auth.authenticate_api_key(api_key: str) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Implement service account API key authentication.

Args:
: api_key: The service account API key.

Returns:
: The authentication context reflecting the authenticated service account.

Raises:
: AuthorizationException: If the service account could not be authorized.

### zenml.zen_server.auth.authenticate_credentials(user_name_or_id: str | UUID | None = None, password: str | None = None, access_token: str | None = None, activation_token: str | None = None) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Verify if user authentication credentials are valid.

This function can be used to validate all supplied user credentials to
cover a range of possibilities:

> * username only - only when the no-auth scheme is used
> * username+password - for basic HTTP authentication or the OAuth2 password
>   grant
> * access token (with embedded user id) - after successful authentication
>   using one of the supported grants
> * username+activation token - for user activation

Args:
: user_name_or_id: The username or user ID.
  password: The password.
  access_token: The access token.
  activation_token: The activation token.

Returns:
: The authenticated account details.

Raises:
: AuthorizationException: If the credentials are invalid.

### zenml.zen_server.auth.authenticate_device(client_id: UUID, device_code: str) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Verify if device authorization credentials are valid.

Args:
: client_id: The OAuth2 client ID.
  device_code: The device code.

Returns:
: The authenticated account details.

Raises:
: OAuthError: If the device authorization credentials are invalid.

### zenml.zen_server.auth.authenticate_external_user(external_access_token: str) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Implement external authentication.

Args:
: external_access_token: The access token used to authenticate the user
  : to the external authenticator.

Returns:
: The authentication context reflecting the authenticated user.

Raises:
: AuthorizationException: If the external user could not be authorized.

### zenml.zen_server.auth.authentication_provider() → Callable[[...], [AuthContext](#zenml.zen_server.auth.AuthContext)]

Returns the authentication provider.

Returns:
: The authentication provider.

Raises:
: ValueError: If the authentication scheme is not supported.

### zenml.zen_server.auth.authorize(token: str = Depends(CookieOAuth2TokenBearer)) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Authenticates any request to the ZenML server with OAuth2 JWT tokens.

Args:
: token: The JWT bearer token to be authenticated.

Returns:
: The authentication context reflecting the authenticated user.

Raises:
: HTTPException: If the JWT token could not be authorized.

### zenml.zen_server.auth.get_auth_context() → [AuthContext](#zenml.zen_server.auth.AuthContext) | None

Returns the current authentication context.

Returns:
: The authentication context.

### zenml.zen_server.auth.http_authentication(credentials: HTTPBasicCredentials = Depends(HTTPBasic)) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Authenticates any request to the ZenML Server with basic HTTP authentication.

Args:
: credentials: HTTP basic auth credentials passed to the request.

Returns:
: The authentication context reflecting the authenticated user.

Raises:
: HTTPException: If the credentials are invalid.

### zenml.zen_server.auth.no_authentication() → [AuthContext](#zenml.zen_server.auth.AuthContext)

Doesn’t authenticate requests to the ZenML server.

Returns:
: The authentication context reflecting the default user.

### zenml.zen_server.auth.oauth2_authentication(token: str = Depends(CookieOAuth2TokenBearer)) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Authenticates any request to the ZenML server with OAuth2 JWT tokens.

Args:
: token: The JWT bearer token to be authenticated.

Returns:
: The authentication context reflecting the authenticated user.

Raises:
: HTTPException: If the JWT token could not be authorized.

### zenml.zen_server.auth.set_auth_context(auth_context: [AuthContext](#zenml.zen_server.auth.AuthContext)) → [AuthContext](#zenml.zen_server.auth.AuthContext)

Sets the current authentication context.

Args:
: auth_context: The authentication context.

Returns:
: The authentication context.

## zenml.zen_server.cloud_utils module

Utils concerning anything concerning the cloud control plane backend.

### *class* zenml.zen_server.cloud_utils.ZenMLCloudConfiguration(\*, api_url: str, oauth2_client_id: str, oauth2_client_secret: str, oauth2_audience: str, auth0_domain: str, \*\*extra_data: Any)

Bases: `BaseModel`

ZenML Pro RBAC configuration.

#### api_url *: str*

#### auth0_domain *: str*

#### *classmethod* from_environment() → [ZenMLCloudConfiguration](#zenml.zen_server.cloud_utils.ZenMLCloudConfiguration)

Get the RBAC configuration from environment variables.

Returns:
: The RBAC configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'api_url': FieldInfo(annotation=str, required=True), 'auth0_domain': FieldInfo(annotation=str, required=True), 'oauth2_audience': FieldInfo(annotation=str, required=True), 'oauth2_client_id': FieldInfo(annotation=str, required=True), 'oauth2_client_secret': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### oauth2_audience *: str*

#### oauth2_client_id *: str*

#### oauth2_client_secret *: str*

### *class* zenml.zen_server.cloud_utils.ZenMLCloudConnection

Bases: `object`

Class to use for communication between server and control plane.

#### get(endpoint: str, params: Dict[str, Any] | None) → Response

Send a GET request using the active session.

Args:
: endpoint: The endpoint to send the request to. This will be appended
  : to the base URL.
  <br/>
  params: Parameters to include in the request.

Raises:
: RuntimeError: If the request failed.
  SubscriptionUpgradeRequiredError: In case the current subscription
  <br/>
  > tier is insufficient for the attempted operation.

Returns:
: The response.

#### post(endpoint: str, params: Dict[str, Any] | None = None, data: Dict[str, Any] | None = None) → Response

Send a POST request using the active session.

Args:
: endpoint: The endpoint to send the request to. This will be appended
  : to the base URL.
  <br/>
  params: Parameters to include in the request.
  data: Data to include in the request.

Raises:
: RuntimeError: If the request failed.

Returns:
: The response.

#### *property* session *: Session*

Authenticate to the ZenML Pro Management Plane.

Returns:
: A requests session with the authentication token.

### zenml.zen_server.cloud_utils.cloud_connection() → [ZenMLCloudConnection](#zenml.zen_server.cloud_utils.ZenMLCloudConnection)

Return the initialized cloud connection.

Returns:
: The cloud connection.

## zenml.zen_server.exceptions module

REST API exception handling.

### *class* zenml.zen_server.exceptions.ErrorModel(\*, detail: Any | None = None)

Bases: `BaseModel`

Base class for error responses.

#### detail *: Any | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'detail': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### zenml.zen_server.exceptions.error_detail(error: Exception, exception_type: Type[Exception] | None = None) → List[str]

Convert an Exception to API representation.

Args:
: error: Exception to convert.
  exception_type: Exception type to use in the error response instead of
  <br/>
  > the type of the supplied exception. This is useful when the raised
  > exception is a subclass of an exception type that is properly
  > handled by the REST API.

Returns:
: List of strings representing the error.

### zenml.zen_server.exceptions.exception_from_response(response: Response) → Exception | None

Convert an error HTTP response to an exception.

Uses the REST_API_EXCEPTIONS list to determine the appropriate exception
class to use based on the response status code and the exception class name
embedded in the response body.

The last entry in the list of exceptions associated with a status code is
used as a fallback if the exception class name in the response body is not
found in the list.

Args:
: response: HTTP error response to convert.

Returns:
: Exception with the appropriate type and arguments, or None if the
  response does not contain an error or the response cannot be unpacked
  into an exception.

### zenml.zen_server.exceptions.http_exception_from_error(error: Exception) → HTTPException

Convert an Exception to a HTTP error response.

Uses the REST_API_EXCEPTIONS list to determine the appropriate status code
associated with the exception type. The exception class name and arguments
are embedded in the HTTP error response body.

The lookup uses the first occurrence of the exception type in the list. If
the exception type is not found in the list, the lookup uses isinstance
to determine the most specific exception type corresponding to the supplied
exception. This allows users to call this method with exception types that
are not directly listed in the REST_API_EXCEPTIONS list.

Args:
: error: Exception to convert.

Returns:
: HTTPException with the appropriate status code and error detail.

## zenml.zen_server.jwt module

Authentication module for ZenML server.

### *class* zenml.zen_server.jwt.JWTToken(\*, user_id: UUID, device_id: UUID | None = None, api_key_id: UUID | None = None, pipeline_id: UUID | None = None, schedule_id: UUID | None = None, claims: Dict[str, Any] = {})

Bases: `BaseModel`

Pydantic object representing a JWT token.

Attributes:
: user_id: The id of the authenticated User.
  device_id: The id of the authenticated device.
  api_key_id: The id of the authenticated API key for which this token
  <br/>
  > was issued.
  <br/>
  pipeline_id: The id of the pipeline for which the token was issued.
  schedule_id: The id of the schedule for which the token was issued.
  claims: The original token claims.

#### api_key_id *: UUID | None*

#### claims *: Dict[str, Any]*

#### *classmethod* decode_token(token: str, verify: bool = True) → [JWTToken](#zenml.zen_server.jwt.JWTToken)

Decodes a JWT access token.

Decodes a JWT access token and returns a JWTToken object with the
information retrieved from its subject claim.

Args:
: token: The encoded JWT token.
  verify: Whether to verify the signature of the token.

Returns:
: The decoded JWT access token.

Raises:
: AuthorizationException: If the token is invalid.

#### device_id *: UUID | None*

#### encode(expires: datetime | None = None) → str

Creates a JWT access token.

Encodes, signs and returns a JWT access token.

Args:
: expires: Datetime after which the token will expire. If not
  : provided, the JWT token will not be set to expire.

Returns:
: The generated access token.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'api_key_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'claims': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'device_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'schedule_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'user_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_id *: UUID | None*

#### schedule_id *: UUID | None*

#### user_id *: UUID*

## zenml.zen_server.rate_limit module

Rate limiting for the ZenML Server.

### *class* zenml.zen_server.rate_limit.RequestLimiter(day_limit: int | None = None, minute_limit: int | None = None)

Bases: `object`

Simple in-memory rate limiter.

#### hit_limiter(request: Request) → None

Increase the number of hits in the limiter.

Args:
: request: Request object.

Raises:
: HTTPException: If the request limit is exceeded.

#### limit_failed_requests(request: Request) → Generator[None, Any, Any]

Limits the number of failed requests.

Args:
: request: Request object.

Yields:
: None

#### reset_limiter(request: Request) → None

Resets the limiter on successful request.

Args:
: request: Request object.

### zenml.zen_server.rate_limit.rate_limit_requests(day_limit: int | None = None, minute_limit: int | None = None) → Callable[[...], Any]

Decorator to handle exceptions in the API.

Args:
: day_limit: Number of requests allowed per day.
  minute_limit: Number of requests allowed per minute.

Returns:
: Decorated function.

## zenml.zen_server.secure_headers module

Secure headers for the ZenML Server.

### zenml.zen_server.secure_headers.initialize_secure_headers() → None

Initialize the secure headers component.

### zenml.zen_server.secure_headers.secure_headers() → Secure

Return the secure headers component.

Returns:
: The secure headers component.

Raises:
: RuntimeError: If the secure headers component is not initialized.

## zenml.zen_server.utils module

Util functions for the ZenML Server.

### zenml.zen_server.utils.feature_gate() → [FeatureGateInterface](zenml.zen_server.feature_gate.md#zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface)

Return the initialized Feature Gate component.

Raises:
: RuntimeError: If the RBAC component is not initialized.

Returns:
: The RBAC component.

### zenml.zen_server.utils.get_active_deployment(local: bool = False) → [ServerDeployment](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment) | None

Get the active local or remote server deployment.

Call this function to retrieve the local or remote server deployment that
was last provisioned on this machine.

Args:
: local: Whether to return the local active deployment or the remote one.

Returns:
: The local or remote active server deployment or None, if no deployment
  was found.

### zenml.zen_server.utils.get_active_server_details() → Tuple[str, int | None]

Get the URL of the current ZenML Server.

When multiple servers are present, the following precedence is used to
determine which server to use:
- If the client is connected to a server, that server has precedence.
- If no server is connected, a server that was deployed remotely has

> precedence over a server that was deployed locally.

Returns:
: The URL and port of the currently active server.

Raises:
: RuntimeError: If no server is active.

### zenml.zen_server.utils.get_ip_location(ip_address: str) → Tuple[str, str, str]

Get the location of the given IP address.

Args:
: ip_address: The IP address to get the location for.

Returns:
: A tuple of city, region, country.

### zenml.zen_server.utils.handle_exceptions(func: F) → F

Decorator to handle exceptions in the API.

Args:
: func: Function to decorate.

Returns:
: Decorated function.

### zenml.zen_server.utils.initialize_feature_gate() → None

Initialize the Feature Gate component.

### zenml.zen_server.utils.initialize_plugins() → None

Initialize the event plugins registry.

### zenml.zen_server.utils.initialize_rbac() → None

Initialize the RBAC component.

### zenml.zen_server.utils.initialize_workload_manager() → None

Initialize the workload manager component.

This does not fail if the source can’t be loaded but only logs a warning.

### zenml.zen_server.utils.initialize_zen_store() → None

Initialize the ZenML Store.

Raises:
: ValueError: If the ZenML Store is using a REST back-end.

### zenml.zen_server.utils.is_user_request(request: Request) → bool

Determine if the incoming request is a user request.

This function checks various aspects of the request to determine
if it’s a user-initiated request or a system request.

Args:
: request: The incoming FastAPI request object.

Returns:
: True if it’s a user request, False otherwise.

### zenml.zen_server.utils.make_dependable(cls: Type[BaseModel]) → Callable[[...], Any]

This function makes a pydantic model usable for fastapi query parameters.

Additionally, it converts InternalServerError\`s that would happen due to
\`pydantic.ValidationError into 422 responses that signal an invalid
request.

Check out [https://github.com/tiangolo/fastapi/issues/1474](https://github.com/tiangolo/fastapi/issues/1474) for context.

Usage:
: def f(model: Model = Depends(make_dependable(Model))):
  : …

UPDATE: Function from above mentioned Github issue was extended to support
multi-input parameters, e.g. tags: List[str]. It needs a default set to Query(<default>),
rather just plain <default>.

Args:
: cls: The model class.

Returns:
: Function to use in FastAPI Depends.

### zenml.zen_server.utils.plugin_flavor_registry() → [PluginFlavorRegistry](zenml.plugins.md#zenml.plugins.plugin_flavor_registry.PluginFlavorRegistry)

Get the plugin flavor registry.

Returns:
: The plugin flavor registry.

### zenml.zen_server.utils.rbac() → [RBACInterface](zenml.zen_server.rbac.md#zenml.zen_server.rbac.rbac_interface.RBACInterface)

Return the initialized RBAC component.

Raises:
: RuntimeError: If the RBAC component is not initialized.

Returns:
: The RBAC component.

### zenml.zen_server.utils.server_config() → [ServerConfiguration](zenml.config.md#zenml.config.server_config.ServerConfiguration)

Returns the ZenML Server configuration.

Returns:
: The ZenML Server configuration.

### zenml.zen_server.utils.verify_admin_status_if_no_rbac(admin_status: bool | None, action: str | None = None) → None

Validate the admin status for sensitive requests.

Only add this check in endpoints meant for admin use only.

Args:
: admin_status: Whether the user is an admin or not. This is only used
  : if explicitly specified in the call and even if passed will be
    ignored, if RBAC is enabled.
  <br/>
  action: The action that is being performed, used for output only.

Raises:
: IllegalOperationError: If the admin status is not valid.

### zenml.zen_server.utils.workload_manager() → [WorkloadManagerInterface](zenml.zen_server.template_execution.md#zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface)

Return the initialized workload manager component.

Raises:
: RuntimeError: If the workload manager component is not initialized.

Returns:
: The workload manager component.

### zenml.zen_server.utils.zen_store() → [SqlZenStore](zenml.zen_stores.md#zenml.zen_stores.sql_zen_store.SqlZenStore)

Initialize the ZenML Store.

Returns:
: The ZenML Store.

Raises:
: RuntimeError: If the ZenML Store has not been initialized.

## zenml.zen_server.zen_server_api module

## Module contents

ZenML Server Implementation.

The ZenML Server is a centralized service meant for use in a collaborative
setting in which stacks, stack components, flavors, pipeline and pipeline runs
can be shared over the network with other users.

You can use the zenml server up command to spin up ZenML server instances
that are either running locally as daemon processes or docker containers, or
to deploy a ZenML server remotely on a managed cloud platform. The other CLI
commands in the same zenml server group can be used to manage the server
instances deployed from your local machine.

To connect the local ZenML client to one of the managed ZenML servers, call
zenml server connect with the name of the server you want to connect to.
