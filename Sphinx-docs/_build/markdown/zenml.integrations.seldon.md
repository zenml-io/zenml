# zenml.integrations.seldon package

## Subpackages

* [zenml.integrations.seldon.custom_deployer package](zenml.integrations.seldon.custom_deployer.md)
  * [Submodules](zenml.integrations.seldon.custom_deployer.md#submodules)
  * [zenml.integrations.seldon.custom_deployer.zenml_custom_model module](zenml.integrations.seldon.custom_deployer.md#module-zenml.integrations.seldon.custom_deployer.zenml_custom_model)
    * [`ZenMLCustomModel`](zenml.integrations.seldon.custom_deployer.md#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel)
      * [`ZenMLCustomModel.load()`](zenml.integrations.seldon.custom_deployer.md#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel.load)
      * [`ZenMLCustomModel.predict()`](zenml.integrations.seldon.custom_deployer.md#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel.predict)
  * [Module contents](zenml.integrations.seldon.custom_deployer.md#module-zenml.integrations.seldon.custom_deployer)
* [zenml.integrations.seldon.flavors package](zenml.integrations.seldon.flavors.md)
  * [Submodules](zenml.integrations.seldon.flavors.md#submodules)
  * [zenml.integrations.seldon.flavors.seldon_model_deployer_flavor module](zenml.integrations.seldon.flavors.md#module-zenml.integrations.seldon.flavors.seldon_model_deployer_flavor)
    * [`SeldonModelDeployerConfig`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig)
      * [`SeldonModelDeployerConfig.base_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.base_url)
      * [`SeldonModelDeployerConfig.kubernetes_context`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.kubernetes_context)
      * [`SeldonModelDeployerConfig.kubernetes_namespace`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.kubernetes_namespace)
      * [`SeldonModelDeployerConfig.kubernetes_secret_name`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.kubernetes_secret_name)
      * [`SeldonModelDeployerConfig.model_computed_fields`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.model_computed_fields)
      * [`SeldonModelDeployerConfig.model_config`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.model_config)
      * [`SeldonModelDeployerConfig.model_fields`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.model_fields)
      * [`SeldonModelDeployerConfig.secret`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig.secret)
    * [`SeldonModelDeployerFlavor`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor)
      * [`SeldonModelDeployerFlavor.config_class`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.config_class)
      * [`SeldonModelDeployerFlavor.docs_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.docs_url)
      * [`SeldonModelDeployerFlavor.implementation_class`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.implementation_class)
      * [`SeldonModelDeployerFlavor.logo_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.logo_url)
      * [`SeldonModelDeployerFlavor.name`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.name)
      * [`SeldonModelDeployerFlavor.sdk_docs_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.sdk_docs_url)
      * [`SeldonModelDeployerFlavor.service_connector_requirements`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor.service_connector_requirements)
  * [Module contents](zenml.integrations.seldon.flavors.md#module-zenml.integrations.seldon.flavors)
    * [`SeldonModelDeployerConfig`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig)
      * [`SeldonModelDeployerConfig.base_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.base_url)
      * [`SeldonModelDeployerConfig.kubernetes_context`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.kubernetes_context)
      * [`SeldonModelDeployerConfig.kubernetes_namespace`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.kubernetes_namespace)
      * [`SeldonModelDeployerConfig.kubernetes_secret_name`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.kubernetes_secret_name)
      * [`SeldonModelDeployerConfig.model_computed_fields`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.model_computed_fields)
      * [`SeldonModelDeployerConfig.model_config`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.model_config)
      * [`SeldonModelDeployerConfig.model_fields`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.model_fields)
      * [`SeldonModelDeployerConfig.secret`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerConfig.secret)
    * [`SeldonModelDeployerFlavor`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor)
      * [`SeldonModelDeployerFlavor.config_class`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.config_class)
      * [`SeldonModelDeployerFlavor.docs_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.docs_url)
      * [`SeldonModelDeployerFlavor.implementation_class`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.implementation_class)
      * [`SeldonModelDeployerFlavor.logo_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.logo_url)
      * [`SeldonModelDeployerFlavor.name`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.name)
      * [`SeldonModelDeployerFlavor.sdk_docs_url`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.sdk_docs_url)
      * [`SeldonModelDeployerFlavor.service_connector_requirements`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor.service_connector_requirements)
* [zenml.integrations.seldon.model_deployers package](zenml.integrations.seldon.model_deployers.md)
  * [Submodules](zenml.integrations.seldon.model_deployers.md#submodules)
  * [zenml.integrations.seldon.model_deployers.seldon_model_deployer module](zenml.integrations.seldon.model_deployers.md#module-zenml.integrations.seldon.model_deployers.seldon_model_deployer)
    * [`SeldonModelDeployer`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer)
      * [`SeldonModelDeployer.FLAVOR`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.FLAVOR)
      * [`SeldonModelDeployer.NAME`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.NAME)
      * [`SeldonModelDeployer.config`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.config)
      * [`SeldonModelDeployer.get_docker_builds()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.get_docker_builds)
      * [`SeldonModelDeployer.get_model_server_info()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.get_model_server_info)
      * [`SeldonModelDeployer.kubernetes_secret_name`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.kubernetes_secret_name)
      * [`SeldonModelDeployer.perform_delete_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.perform_delete_model)
      * [`SeldonModelDeployer.perform_deploy_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.perform_deploy_model)
      * [`SeldonModelDeployer.perform_start_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.perform_start_model)
      * [`SeldonModelDeployer.perform_stop_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.perform_stop_model)
      * [`SeldonModelDeployer.seldon_client`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.seldon_client)
      * [`SeldonModelDeployer.validator`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer.validator)
  * [Module contents](zenml.integrations.seldon.model_deployers.md#module-zenml.integrations.seldon.model_deployers)
    * [`SeldonModelDeployer`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer)
      * [`SeldonModelDeployer.FLAVOR`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.FLAVOR)
      * [`SeldonModelDeployer.NAME`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.NAME)
      * [`SeldonModelDeployer.config`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.config)
      * [`SeldonModelDeployer.get_docker_builds()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.get_docker_builds)
      * [`SeldonModelDeployer.get_model_server_info()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.get_model_server_info)
      * [`SeldonModelDeployer.kubernetes_secret_name`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.kubernetes_secret_name)
      * [`SeldonModelDeployer.perform_delete_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.perform_delete_model)
      * [`SeldonModelDeployer.perform_deploy_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.perform_deploy_model)
      * [`SeldonModelDeployer.perform_start_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.perform_start_model)
      * [`SeldonModelDeployer.perform_stop_model()`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.perform_stop_model)
      * [`SeldonModelDeployer.seldon_client`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.seldon_client)
      * [`SeldonModelDeployer.validator`](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.SeldonModelDeployer.validator)
* [zenml.integrations.seldon.secret_schemas package](zenml.integrations.seldon.secret_schemas.md)
  * [Submodules](zenml.integrations.seldon.secret_schemas.md#submodules)
  * [zenml.integrations.seldon.secret_schemas.secret_schemas module](zenml.integrations.seldon.secret_schemas.md#module-zenml.integrations.seldon.secret_schemas.secret_schemas)
    * [`SeldonAzureSecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema)
      * [`SeldonAzureSecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.model_computed_fields)
      * [`SeldonAzureSecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.model_config)
      * [`SeldonAzureSecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.model_fields)
      * [`SeldonAzureSecretSchema.rclone_config_az_account`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_account)
      * [`SeldonAzureSecretSchema.rclone_config_az_client_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_client_id)
      * [`SeldonAzureSecretSchema.rclone_config_az_client_secret`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_client_secret)
      * [`SeldonAzureSecretSchema.rclone_config_az_env_auth`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_env_auth)
      * [`SeldonAzureSecretSchema.rclone_config_az_key`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_key)
      * [`SeldonAzureSecretSchema.rclone_config_az_sas_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_sas_url)
      * [`SeldonAzureSecretSchema.rclone_config_az_tenant`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_tenant)
      * [`SeldonAzureSecretSchema.rclone_config_az_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_type)
      * [`SeldonAzureSecretSchema.rclone_config_az_use_msi`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_use_msi)
    * [`SeldonGSSecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema)
      * [`SeldonGSSecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.model_computed_fields)
      * [`SeldonGSSecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.model_config)
      * [`SeldonGSSecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.model_fields)
      * [`SeldonGSSecretSchema.rclone_config_gs_anonymous`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_anonymous)
      * [`SeldonGSSecretSchema.rclone_config_gs_auth_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_auth_url)
      * [`SeldonGSSecretSchema.rclone_config_gs_client_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_client_id)
      * [`SeldonGSSecretSchema.rclone_config_gs_client_secret`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_client_secret)
      * [`SeldonGSSecretSchema.rclone_config_gs_project_number`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_project_number)
      * [`SeldonGSSecretSchema.rclone_config_gs_service_account_credentials`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_service_account_credentials)
      * [`SeldonGSSecretSchema.rclone_config_gs_token`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_token)
      * [`SeldonGSSecretSchema.rclone_config_gs_token_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_token_url)
      * [`SeldonGSSecretSchema.rclone_config_gs_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_type)
    * [`SeldonS3SecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema)
      * [`SeldonS3SecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.model_computed_fields)
      * [`SeldonS3SecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.model_config)
      * [`SeldonS3SecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.model_fields)
      * [`SeldonS3SecretSchema.rclone_config_s3_access_key_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_access_key_id)
      * [`SeldonS3SecretSchema.rclone_config_s3_endpoint`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_endpoint)
      * [`SeldonS3SecretSchema.rclone_config_s3_env_auth`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_env_auth)
      * [`SeldonS3SecretSchema.rclone_config_s3_provider`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_provider)
      * [`SeldonS3SecretSchema.rclone_config_s3_region`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_region)
      * [`SeldonS3SecretSchema.rclone_config_s3_secret_access_key`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_secret_access_key)
      * [`SeldonS3SecretSchema.rclone_config_s3_session_token`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_session_token)
      * [`SeldonS3SecretSchema.rclone_config_s3_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_type)
  * [Module contents](zenml.integrations.seldon.secret_schemas.md#module-zenml.integrations.seldon.secret_schemas)
    * [`SeldonAzureSecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema)
      * [`SeldonAzureSecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.model_computed_fields)
      * [`SeldonAzureSecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.model_config)
      * [`SeldonAzureSecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.model_fields)
      * [`SeldonAzureSecretSchema.rclone_config_az_account`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_account)
      * [`SeldonAzureSecretSchema.rclone_config_az_client_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_client_id)
      * [`SeldonAzureSecretSchema.rclone_config_az_client_secret`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_client_secret)
      * [`SeldonAzureSecretSchema.rclone_config_az_env_auth`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_env_auth)
      * [`SeldonAzureSecretSchema.rclone_config_az_key`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_key)
      * [`SeldonAzureSecretSchema.rclone_config_az_sas_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_sas_url)
      * [`SeldonAzureSecretSchema.rclone_config_az_tenant`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_tenant)
      * [`SeldonAzureSecretSchema.rclone_config_az_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_type)
      * [`SeldonAzureSecretSchema.rclone_config_az_use_msi`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema.rclone_config_az_use_msi)
    * [`SeldonGSSecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema)
      * [`SeldonGSSecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.model_computed_fields)
      * [`SeldonGSSecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.model_config)
      * [`SeldonGSSecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.model_fields)
      * [`SeldonGSSecretSchema.rclone_config_gs_anonymous`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_anonymous)
      * [`SeldonGSSecretSchema.rclone_config_gs_auth_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_auth_url)
      * [`SeldonGSSecretSchema.rclone_config_gs_client_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_client_id)
      * [`SeldonGSSecretSchema.rclone_config_gs_client_secret`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_client_secret)
      * [`SeldonGSSecretSchema.rclone_config_gs_project_number`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_project_number)
      * [`SeldonGSSecretSchema.rclone_config_gs_service_account_credentials`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_service_account_credentials)
      * [`SeldonGSSecretSchema.rclone_config_gs_token`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_token)
      * [`SeldonGSSecretSchema.rclone_config_gs_token_url`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_token_url)
      * [`SeldonGSSecretSchema.rclone_config_gs_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema.rclone_config_gs_type)
    * [`SeldonS3SecretSchema`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema)
      * [`SeldonS3SecretSchema.model_computed_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.model_computed_fields)
      * [`SeldonS3SecretSchema.model_config`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.model_config)
      * [`SeldonS3SecretSchema.model_fields`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.model_fields)
      * [`SeldonS3SecretSchema.rclone_config_s3_access_key_id`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_access_key_id)
      * [`SeldonS3SecretSchema.rclone_config_s3_endpoint`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_endpoint)
      * [`SeldonS3SecretSchema.rclone_config_s3_env_auth`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_env_auth)
      * [`SeldonS3SecretSchema.rclone_config_s3_provider`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_provider)
      * [`SeldonS3SecretSchema.rclone_config_s3_region`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_region)
      * [`SeldonS3SecretSchema.rclone_config_s3_secret_access_key`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_secret_access_key)
      * [`SeldonS3SecretSchema.rclone_config_s3_session_token`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_session_token)
      * [`SeldonS3SecretSchema.rclone_config_s3_type`](zenml.integrations.seldon.secret_schemas.md#zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema.rclone_config_s3_type)
* [zenml.integrations.seldon.services package](zenml.integrations.seldon.services.md)
  * [Submodules](zenml.integrations.seldon.services.md#submodules)
  * [zenml.integrations.seldon.services.seldon_deployment module](zenml.integrations.seldon.services.md#module-zenml.integrations.seldon.services.seldon_deployment)
    * [`SeldonDeploymentConfig`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig)
      * [`SeldonDeploymentConfig.create_from_deployment()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.create_from_deployment)
      * [`SeldonDeploymentConfig.extra_args`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.extra_args)
      * [`SeldonDeploymentConfig.get_seldon_deployment_annotations()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.get_seldon_deployment_annotations)
      * [`SeldonDeploymentConfig.get_seldon_deployment_labels()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.get_seldon_deployment_labels)
      * [`SeldonDeploymentConfig.implementation`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.implementation)
      * [`SeldonDeploymentConfig.is_custom_deployment`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.is_custom_deployment)
      * [`SeldonDeploymentConfig.model_computed_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_computed_fields)
      * [`SeldonDeploymentConfig.model_config`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_config)
      * [`SeldonDeploymentConfig.model_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_fields)
      * [`SeldonDeploymentConfig.model_metadata`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_metadata)
      * [`SeldonDeploymentConfig.model_name`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_name)
      * [`SeldonDeploymentConfig.model_uri`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.model_uri)
      * [`SeldonDeploymentConfig.parameters`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.parameters)
      * [`SeldonDeploymentConfig.replicas`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.replicas)
      * [`SeldonDeploymentConfig.resources`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.resources)
      * [`SeldonDeploymentConfig.secret_name`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.secret_name)
      * [`SeldonDeploymentConfig.serviceAccountName`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.serviceAccountName)
      * [`SeldonDeploymentConfig.spec`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.spec)
      * [`SeldonDeploymentConfig.type`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig.type)
    * [`SeldonDeploymentService`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService)
      * [`SeldonDeploymentService.SERVICE_TYPE`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.SERVICE_TYPE)
      * [`SeldonDeploymentService.check_status()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.check_status)
      * [`SeldonDeploymentService.config`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.config)
      * [`SeldonDeploymentService.create_from_deployment()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.create_from_deployment)
      * [`SeldonDeploymentService.deprovision()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.deprovision)
      * [`SeldonDeploymentService.get_logs()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.get_logs)
      * [`SeldonDeploymentService.model_computed_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.model_computed_fields)
      * [`SeldonDeploymentService.model_config`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.model_config)
      * [`SeldonDeploymentService.model_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.model_fields)
      * [`SeldonDeploymentService.predict()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.predict)
      * [`SeldonDeploymentService.prediction_url`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.prediction_url)
      * [`SeldonDeploymentService.provision()`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.provision)
      * [`SeldonDeploymentService.seldon_deployment_name`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.seldon_deployment_name)
      * [`SeldonDeploymentService.status`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.status)
      * [`SeldonDeploymentService.type`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService.type)
    * [`SeldonDeploymentServiceStatus`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus)
      * [`SeldonDeploymentServiceStatus.model_computed_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus.model_computed_fields)
      * [`SeldonDeploymentServiceStatus.model_config`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus.model_config)
      * [`SeldonDeploymentServiceStatus.model_fields`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus.model_fields)
      * [`SeldonDeploymentServiceStatus.type`](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus.type)
  * [Module contents](zenml.integrations.seldon.services.md#module-zenml.integrations.seldon.services)
* [zenml.integrations.seldon.steps package](zenml.integrations.seldon.steps.md)
  * [Submodules](zenml.integrations.seldon.steps.md#submodules)
  * [zenml.integrations.seldon.steps.seldon_deployer module](zenml.integrations.seldon.steps.md#module-zenml.integrations.seldon.steps.seldon_deployer)
  * [Module contents](zenml.integrations.seldon.steps.md#module-zenml.integrations.seldon.steps)

## Submodules

## zenml.integrations.seldon.constants module

Seldon constants.

## zenml.integrations.seldon.seldon_client module

Implementation of the Seldon client for ZenML.

### *class* zenml.integrations.seldon.seldon_client.SeldonClient(context: str | None, namespace: str | None, kube_client: ApiClient | None = None)

Bases: `object`

A client for interacting with Seldon Deployments.

#### create_deployment(deployment: [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment), poll_timeout: int = 0) → [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment)

Create a Seldon Core deployment resource.

Args:
: deployment: the Seldon Core deployment resource to create
  poll_timeout: the maximum time to wait for the deployment to become
  <br/>
  > available or to fail. If set to 0, the function will return
  > immediately without checking the deployment status. If a timeout
  > occurs and the deployment is still pending creation, it will
  > be returned anyway and no exception will be raised.

Returns:
: the created Seldon Core deployment resource with updated status.

Raises:
: SeldonDeploymentExistsError: if a deployment with the same name
  : already exists.
  <br/>
  SeldonClientError: if an unknown error occurs during the creation of
  : the deployment.

#### create_or_update_secret(name: str, secret_values: Dict[str, Any]) → None

Create or update a Kubernetes Secret resource.

Args:
: name: the name of the Secret resource to create.
  secret_values: secret key-values that should be
  <br/>
  > stored in the Secret resource.

Raises:
: SeldonClientError: if an unknown error occurs during the creation of
  : the secret.
  <br/>
  k8s_client.rest.ApiException: unexpected error.

#### delete_deployment(name: str, force: bool = False, poll_timeout: int = 0) → None

Delete a Seldon Core deployment resource managed by ZenML.

Args:
: name: the name of the Seldon Core deployment resource to delete.
  force: if True, the deployment deletion will be forced (the graceful
  <br/>
  > period will be set to zero).
  <br/>
  poll_timeout: the maximum time to wait for the deployment to be
  : deleted. If set to 0, the function will return immediately
    without checking the deployment status. If a timeout
    occurs and the deployment still exists, this method will
    return and no exception will be raised.

Raises:
: SeldonClientError: if an unknown error occurs during the deployment
  : removal.

#### delete_secret(name: str) → None

Delete a Kubernetes Secret resource managed by ZenML.

Args:
: name: the name of the Kubernetes Secret resource to delete.

Raises:
: SeldonClientError: if an unknown error occurs during the removal
  : of the secret.

#### find_deployments(name: str | None = None, labels: Dict[str, str] | None = None, fields: Dict[str, str] | None = None) → List[[SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment)]

Find all ZenML-managed Seldon Core deployment resources matching the given criteria.

Args:
: name: optional name of the deployment resource to find.
  fields: optional selector to restrict the list of returned
  <br/>
  > Seldon deployments by their fields. Defaults to everything.
  <br/>
  labels: optional selector to restrict the list of returned
  : Seldon deployments by their labels. Defaults to everything.

Returns:
: List of Seldon Core deployments that match the given criteria.

Raises:
: SeldonClientError: if an unknown error occurs while fetching
  : the deployments.

#### get_deployment(name: str) → [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment)

Get a ZenML managed Seldon Core deployment resource by name.

Args:
: name: the name of the Seldon Core deployment resource to fetch.

Returns:
: The Seldon Core deployment resource.

Raises:
: SeldonDeploymentNotFoundError: if the deployment resource cannot
  : be found or is not managed by ZenML.
  <br/>
  SeldonClientError: if an unknown error occurs while fetching
  : the deployment.

#### get_deployment_logs(name: str, follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Get the logs of a Seldon Core deployment resource.

Args:
: name: the name of the Seldon Core deployment to get logs for.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

Yields:
: The next log line.

Raises:
: SeldonClientError: if an unknown error occurs while fetching
  : the logs.

#### *property* namespace *: str*

Returns the Kubernetes namespace in use by the client.

Returns:
: The Kubernetes namespace in use by the client.

Raises:
: RuntimeError: if the namespace has not been configured.

#### *static* sanitize_labels(labels: Dict[str, str]) → None

Update the label values to be valid Kubernetes labels.

See:
[https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set)

Args:
: labels: the labels to sanitize.

#### update_deployment(deployment: [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment), poll_timeout: int = 0) → [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment)

Update a Seldon Core deployment resource.

Args:
: deployment: the Seldon Core deployment resource to update
  poll_timeout: the maximum time to wait for the deployment to become
  <br/>
  > available or to fail. If set to 0, the function will return
  > immediately without checking the deployment status. If a timeout
  > occurs and the deployment is still pending creation, it will
  > be returned anyway and no exception will be raised.

Returns:
: the updated Seldon Core deployment resource with updated status.

Raises:
: SeldonClientError: if an unknown error occurs while updating the
  : deployment.

### *exception* zenml.integrations.seldon.seldon_client.SeldonClientError

Bases: `Exception`

Base exception class for all exceptions raised by the SeldonClient.

### *exception* zenml.integrations.seldon.seldon_client.SeldonClientTimeout

Bases: [`SeldonClientError`](#zenml.integrations.seldon.seldon_client.SeldonClientError)

Raised when the Seldon client timed out while waiting for a resource to reach the expected status.

### *class* zenml.integrations.seldon.seldon_client.SeldonDeployment(\*, kind: Literal['SeldonDeployment'] = 'SeldonDeployment', apiVersion: Literal['machinelearning.seldon.io/v1'] = 'machinelearning.seldon.io/v1', metadata: [SeldonDeploymentMetadata](#zenml.integrations.seldon.seldon_client.SeldonDeploymentMetadata), spec: [SeldonDeploymentSpec](#zenml.integrations.seldon.seldon_client.SeldonDeploymentSpec), status: [SeldonDeploymentStatus](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatus) | None = None)

Bases: `BaseModel`

A Seldon Core deployment CRD.

This is a Pydantic representation of some of the fields in the Seldon Core
CRD (documented here:
[https://docs.seldon.io/projects/seldon-core/en/latest/reference/seldon-deployment.html](https://docs.seldon.io/projects/seldon-core/en/latest/reference/seldon-deployment.html)).

Note that not all fields are represented, only those that are relevant to
the ZenML integration. The fields that are not represented are silently
ignored when the Seldon Deployment is created or updated from an external
SeldonDeployment CRD representation.

Attributes:
: kind: Kubernetes kind field.
  apiVersion: Kubernetes apiVersion field.
  metadata: Kubernetes metadata field.
  spec: Seldon Deployment spec entry.
  status: Seldon Deployment status.

#### apiVersion *: Literal['machinelearning.seldon.io/v1']*

#### *classmethod* build(name: str | None = None, model_uri: str | None = None, model_name: str | None = None, implementation: str | None = None, parameters: List[[SeldonDeploymentPredictorParameter](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter)] | None = None, engineResources: [SeldonResourceRequirements](#zenml.integrations.seldon.seldon_client.SeldonResourceRequirements) | None = None, secret_name: str | None = None, labels: Dict[str, str] | None = None, annotations: Dict[str, str] | None = None, is_custom_deployment: bool | None = False, spec: Dict[Any, Any] | None = None, serviceAccountName: str | None = None) → [SeldonDeployment](#zenml.integrations.seldon.seldon_client.SeldonDeployment)

Build a basic Seldon Deployment object.

Args:
: name: The name of the Seldon Deployment. If not explicitly passed,
  : a unique name is autogenerated.
  <br/>
  model_uri: The URI of the model.
  model_name: The name of the model.
  implementation: The implementation of the model.
  parameters: The predictor graph parameters.
  engineResources: The resources to be allocated to the model.
  secret_name: The name of the Kubernetes secret containing
  <br/>
  > environment variable values (e.g. with credentials for the
  > artifact store) to use with the deployment service.
  <br/>
  labels: A dictionary of labels to apply to the Seldon Deployment.
  annotations: A dictionary of annotations to apply to the Seldon
  <br/>
  > Deployment.
  <br/>
  spec: A Kubernetes pod spec to use for the Seldon Deployment.
  is_custom_deployment: Whether the Seldon Deployment is a custom
  <br/>
  > or a built-in one.
  <br/>
  serviceAccountName: The name of the service account to associate
  : with the predictive unit container.

Returns:
: A minimal SeldonDeployment object built from the provided
  parameters.

#### get_error() → str | None

Get a message describing the error, if in an error state.

Returns:
: A message describing the error, if in an error state, otherwise
  None.

#### get_pending_message() → str | None

Get a message describing the pending conditions of the Seldon Deployment.

Returns:
: A message describing the pending condition of the Seldon
  Deployment, or None, if no conditions are pending.

#### is_available() → bool

Checks if the Seldon Deployment is in an available state.

Returns:
: True if the Seldon Deployment is available, False otherwise.

#### is_failed() → bool

Checks if the Seldon Deployment is in a failed state.

Returns:
: True if the Seldon Deployment is failed, False otherwise.

#### is_managed_by_zenml() → bool

Checks if this Seldon Deployment is managed by ZenML.

The convention used to differentiate between SeldonDeployment instances
that are managed by ZenML and those that are not is to set the app
label value to zenml.

Returns:
: True if the Seldon Deployment is managed by ZenML, False
  otherwise.

#### is_pending() → bool

Checks if the Seldon Deployment is in a pending state.

Returns:
: True if the Seldon Deployment is pending, False otherwise.

#### kind *: Literal['SeldonDeployment']*

#### mark_as_managed_by_zenml() → None

Marks this Seldon Deployment as managed by ZenML.

The convention used to differentiate between SeldonDeployment instances
that are managed by ZenML and those that are not is to set the app
label value to zenml.

#### metadata *: [SeldonDeploymentMetadata](#zenml.integrations.seldon.seldon_client.SeldonDeploymentMetadata)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'apiVersion': FieldInfo(annotation=Literal['machinelearning.seldon.io/v1'], required=False, default='machinelearning.seldon.io/v1'), 'kind': FieldInfo(annotation=Literal['SeldonDeployment'], required=False, default='SeldonDeployment'), 'metadata': FieldInfo(annotation=SeldonDeploymentMetadata, required=True), 'spec': FieldInfo(annotation=SeldonDeploymentSpec, required=True), 'status': FieldInfo(annotation=Union[SeldonDeploymentStatus, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* name *: str*

Returns the name of this Seldon Deployment.

This is just a shortcut for self.metadata.name.

Returns:
: The name of this Seldon Deployment.

#### spec *: [SeldonDeploymentSpec](#zenml.integrations.seldon.seldon_client.SeldonDeploymentSpec)*

#### *property* state *: [SeldonDeploymentStatusState](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusState)*

The state of the Seldon Deployment.

Returns:
: The state of the Seldon Deployment.

#### status *: [SeldonDeploymentStatus](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatus) | None*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentComponentSpecs(\*, spec: Dict[str, Any] | None = None)

Bases: `BaseModel`

Component specs for a Seldon Deployment.

Attributes:
: spec: the component spec.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'spec': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### spec *: Dict[str, Any] | None*

### *exception* zenml.integrations.seldon.seldon_client.SeldonDeploymentExistsError

Bases: [`SeldonClientError`](#zenml.integrations.seldon.seldon_client.SeldonClientError)

Raised when a SeldonDeployment resource cannot be created because a resource with the same name already exists.

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentMetadata(\*, name: str, labels: Dict[str, str] = None, annotations: Dict[str, str] = None, creationTimestamp: str | None = None)

Bases: `BaseModel`

Metadata for a Seldon Deployment.

Attributes:
: name: the name of the Seldon Deployment.
  labels: Kubernetes labels for the Seldon Deployment.
  annotations: Kubernetes annotations for the Seldon Deployment.
  creationTimestamp: the creation timestamp of the Seldon Deployment.

#### annotations *: Dict[str, str]*

#### creationTimestamp *: str | None*

#### labels *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'annotations': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict), 'creationTimestamp': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'labels': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict), 'name': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *exception* zenml.integrations.seldon.seldon_client.SeldonDeploymentNotFoundError

Bases: [`SeldonClientError`](#zenml.integrations.seldon.seldon_client.SeldonClientError)

Raised when a particular SeldonDeployment resource is not found or is not managed by ZenML.

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnit(\*, name: str, type: [SeldonDeploymentPredictiveUnitType](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnitType) | None = SeldonDeploymentPredictiveUnitType.MODEL, implementation: str | None = None, modelUri: str | None = None, parameters: List[[SeldonDeploymentPredictorParameter](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter)] | None = None, serviceAccountName: str | None = None, envSecretRefName: str | None = None, children: List[[SeldonDeploymentPredictiveUnit](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnit)] | None = None)

Bases: `BaseModel`

Seldon Deployment predictive unit.

Attributes:
: name: the name of the predictive unit.
  type: predictive unit type.
  implementation: the Seldon Core implementation used to serve the model.
  modelUri: URI of the model (or models) to serve.
  serviceAccountName: the name of the service account to associate with
  <br/>
  > the predictive unit container.
  <br/>
  envSecretRefName: the name of a Kubernetes secret that contains
  : environment variables (e.g. credentials) to be configured for the
    predictive unit container.
  <br/>
  children: a list of child predictive units that together make up the
  : model serving graph.

#### children *: List[[SeldonDeploymentPredictiveUnit](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnit)] | None*

#### envSecretRefName *: str | None*

#### implementation *: str | None*

#### modelUri *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'children': FieldInfo(annotation=Union[List[SeldonDeploymentPredictiveUnit], NoneType], required=False, default=None), 'envSecretRefName': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'implementation': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'modelUri': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'parameters': FieldInfo(annotation=Union[List[SeldonDeploymentPredictorParameter], NoneType], required=False, default=None), 'serviceAccountName': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'type': FieldInfo(annotation=Union[SeldonDeploymentPredictiveUnitType, NoneType], required=False, default=<SeldonDeploymentPredictiveUnitType.MODEL: 'MODEL'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### parameters *: List[[SeldonDeploymentPredictorParameter](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter)] | None*

#### serviceAccountName *: str | None*

#### type *: [SeldonDeploymentPredictiveUnitType](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnitType) | None*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnitType(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Predictive unit types for a Seldon Deployment.

#### COMBINER *= 'COMBINER'*

#### MODEL *= 'MODEL'*

#### OUTPUT_TRANSFORMER *= 'OUTPUT_TRANSFORMER'*

#### ROUTER *= 'ROUTER'*

#### TRANSFORMER *= 'TRANSFORMER'*

#### UNKNOWN_TYPE *= 'UNKNOWN_TYPE'*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictor(\*, name: str, replicas: int = 1, graph: [SeldonDeploymentPredictiveUnit](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnit), engineResources: [SeldonResourceRequirements](#zenml.integrations.seldon.seldon_client.SeldonResourceRequirements) | None = None, componentSpecs: List[[SeldonDeploymentComponentSpecs](#zenml.integrations.seldon.seldon_client.SeldonDeploymentComponentSpecs)] | None = None)

Bases: `BaseModel`

Seldon Deployment predictor.

Attributes:
: name: the name of the predictor.
  replicas: the number of pod replicas for the predictor.
  graph: the serving graph composed of one or more predictive units.

#### componentSpecs *: List[[SeldonDeploymentComponentSpecs](#zenml.integrations.seldon.seldon_client.SeldonDeploymentComponentSpecs)] | None*

#### engineResources *: [SeldonResourceRequirements](#zenml.integrations.seldon.seldon_client.SeldonResourceRequirements) | None*

#### graph *: [SeldonDeploymentPredictiveUnit](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictiveUnit)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'componentSpecs': FieldInfo(annotation=Union[List[SeldonDeploymentComponentSpecs], NoneType], required=False, default=None), 'engineResources': FieldInfo(annotation=Union[SeldonResourceRequirements, NoneType], required=False, default_factory=SeldonResourceRequirements), 'graph': FieldInfo(annotation=SeldonDeploymentPredictiveUnit, required=True), 'name': FieldInfo(annotation=str, required=True), 'replicas': FieldInfo(annotation=int, required=False, default=1)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### replicas *: int*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter(\*, name: str = '', type: str = '', value: str = '')

Bases: `BaseModel`

Parameter for Seldon Deployment predictor.

Attributes:
: name: parameter name
  type: parameter, can be INT, FLOAT, DOUBLE, STRING, BOOL
  value: parameter value

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=str, required=False, default=''), 'value': FieldInfo(annotation=str, required=False, default='')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: str*

#### value *: str*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentSpec(\*, name: str, protocol: str | None = None, predictors: List[[SeldonDeploymentPredictor](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictor)], replicas: int = 1)

Bases: `BaseModel`

Spec for a Seldon Deployment.

Attributes:
: name: the name of the Seldon Deployment.
  protocol: the API protocol used for the Seldon Deployment.
  predictors: a list of predictors that make up the serving graph.
  replicas: the default number of pod replicas used for the predictors.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=str, required=True), 'predictors': FieldInfo(annotation=List[SeldonDeploymentPredictor], required=True), 'protocol': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'replicas': FieldInfo(annotation=int, required=False, default=1)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### predictors *: List[[SeldonDeploymentPredictor](#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictor)]*

#### protocol *: str | None*

#### replicas *: int*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentStatus(\*, state: [SeldonDeploymentStatusState](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusState) = SeldonDeploymentStatusState.UNKNOWN, description: str | None = None, replicas: int | None = None, address: [SeldonDeploymentStatusAddress](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusAddress) | None = None, conditions: List[[SeldonDeploymentStatusCondition](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusCondition)])

Bases: `BaseModel`

The status of a Seldon Deployment.

Attributes:
: state: the current state of the Seldon Deployment.
  description: a human-readable description of the current state.
  replicas: the current number of running pod replicas
  address: the address where the Seldon Deployment API can be accessed.
  conditions: the list of Kubernetes conditions for the Seldon Deployment.

#### address *: [SeldonDeploymentStatusAddress](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusAddress) | None*

#### conditions *: List[[SeldonDeploymentStatusCondition](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusCondition)]*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'address': FieldInfo(annotation=Union[SeldonDeploymentStatusAddress, NoneType], required=False, default=None), 'conditions': FieldInfo(annotation=List[SeldonDeploymentStatusCondition], required=True), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'replicas': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'state': FieldInfo(annotation=SeldonDeploymentStatusState, required=False, default=<SeldonDeploymentStatusState.UNKNOWN: 'Unknown'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### replicas *: int | None*

#### state *: [SeldonDeploymentStatusState](#zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusState)*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusAddress(\*, url: str)

Bases: `BaseModel`

The status address for a Seldon Deployment.

Attributes:
: url: the URL where the Seldon Deployment API can be accessed internally.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### url *: str*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusCondition(\*, type: str, status: bool, reason: str | None = None, message: str | None = None)

Bases: `BaseModel`

The Kubernetes status condition entry for a Seldon Deployment.

Attributes:
: type: Type of runtime condition.
  status: Status of the condition.
  reason: Brief CamelCase string containing reason for the condition’s
  <br/>
  > last transition.
  <br/>
  message: Human-readable message indicating details about last
  : transition.

#### message *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'message': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'reason': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'status': FieldInfo(annotation=bool, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### reason *: str | None*

#### status *: bool*

#### type *: str*

### *class* zenml.integrations.seldon.seldon_client.SeldonDeploymentStatusState(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Possible state values for a Seldon Deployment.

#### AVAILABLE *= 'Available'*

#### CREATING *= 'Creating'*

#### FAILED *= 'Failed'*

#### UNKNOWN *= 'Unknown'*

### *class* zenml.integrations.seldon.seldon_client.SeldonResourceRequirements(\*, limits: Dict[str, str] = None, requests: Dict[str, str] = None)

Bases: `BaseModel`

Resource requirements for a Seldon deployed model.

Attributes:
: limits: an upper limit of resources to be used by the model
  requests: resources requested by the model

#### limits *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'limits': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict), 'requests': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### requests *: Dict[str, str]*

### zenml.integrations.seldon.seldon_client.create_seldon_core_custom_spec(model_uri: str | None, custom_docker_image: str | None, secret_name: str | None, command: List[str] | None, container_registry_secret_name: str | None = None) → V1PodSpec

Create a custom pod spec for the seldon core container.

Args:
: model_uri: The URI of the model to load.
  custom_docker_image: The docker image to use.
  secret_name: The name of the Kubernetes secret to use.
  command: The command to run in the container.
  container_registry_secret_name: The name of the secret to use for docker
  <br/>
  > image pull.

Returns:
: A pod spec for the seldon core container.

## Module contents

Initialization of the Seldon integration.

The Seldon Core integration allows you to use the Seldon Core model serving
platform to implement continuous model deployment.

### *class* zenml.integrations.seldon.SeldonIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Seldon Core integration for ZenML.

#### NAME *= 'seldon'*

#### REQUIREMENTS *: List[str]* *= ['kubernetes==18.20.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kubernetes', 'numpy']*

#### *classmethod* activate() → None

Activate the Seldon Core integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Seldon Core.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
