# zenml.zen_stores package

## Subpackages

* [zenml.zen_stores.migrations package](zenml.zen_stores.migrations.md)
  * [Submodules](zenml.zen_stores.migrations.md#submodules)
  * [zenml.zen_stores.migrations.alembic module](zenml.zen_stores.migrations.md#module-zenml.zen_stores.migrations.alembic)
    * [`Alembic`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic)
      * [`Alembic.current_revisions()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.current_revisions)
      * [`Alembic.db_is_empty()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.db_is_empty)
      * [`Alembic.downgrade()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.downgrade)
      * [`Alembic.head_revisions()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.head_revisions)
      * [`Alembic.run_migrations()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.run_migrations)
      * [`Alembic.stamp()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.stamp)
      * [`Alembic.upgrade()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic.upgrade)
    * [`AlembicVersion`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.AlembicVersion)
      * [`AlembicVersion.version_num`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.AlembicVersion.version_num)
    * [`include_object()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.include_object)
  * [zenml.zen_stores.migrations.utils module](zenml.zen_stores.migrations.md#module-zenml.zen_stores.migrations.utils)
    * [`MigrationUtils`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils)
      * [`MigrationUtils.backup_database_to_db()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.backup_database_to_db)
      * [`MigrationUtils.backup_database_to_file()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.backup_database_to_file)
      * [`MigrationUtils.backup_database_to_memory()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.backup_database_to_memory)
      * [`MigrationUtils.backup_database_to_storage()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.backup_database_to_storage)
      * [`MigrationUtils.connect_args`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.connect_args)
      * [`MigrationUtils.create_database()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.create_database)
      * [`MigrationUtils.create_engine()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.create_engine)
      * [`MigrationUtils.database_exists()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.database_exists)
      * [`MigrationUtils.drop_database()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.drop_database)
      * [`MigrationUtils.engine`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.engine)
      * [`MigrationUtils.engine_args`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.engine_args)
      * [`MigrationUtils.is_mysql_missing_database_error()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.is_mysql_missing_database_error)
      * [`MigrationUtils.master_engine`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.master_engine)
      * [`MigrationUtils.model_computed_fields`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.model_computed_fields)
      * [`MigrationUtils.model_config`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.model_config)
      * [`MigrationUtils.model_fields`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.model_fields)
      * [`MigrationUtils.model_post_init()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.model_post_init)
      * [`MigrationUtils.restore_database_from_db()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.restore_database_from_db)
      * [`MigrationUtils.restore_database_from_file()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.restore_database_from_file)
      * [`MigrationUtils.restore_database_from_memory()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.restore_database_from_memory)
      * [`MigrationUtils.restore_database_from_storage()`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.restore_database_from_storage)
      * [`MigrationUtils.url`](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils.url)
  * [Module contents](zenml.zen_stores.migrations.md#module-zenml.zen_stores.migrations)
* [zenml.zen_stores.schemas package](zenml.zen_stores.schemas.md)
  * [Submodules](zenml.zen_stores.schemas.md#submodules)
  * [zenml.zen_stores.schemas.action_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.action_schemas)
    * [`ActionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema)
      * [`ActionSchema.auth_window`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.auth_window)
      * [`ActionSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.configuration)
      * [`ActionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.created)
      * [`ActionSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.description)
      * [`ActionSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.flavor)
      * [`ActionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.from_request)
      * [`ActionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.id)
      * [`ActionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.model_computed_fields)
      * [`ActionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.model_config)
      * [`ActionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.model_fields)
      * [`ActionSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.name)
      * [`ActionSchema.plugin_subtype`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.plugin_subtype)
      * [`ActionSchema.service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.service_account)
      * [`ActionSchema.service_account_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.service_account_id)
      * [`ActionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.to_model)
      * [`ActionSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.triggers)
      * [`ActionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.update)
      * [`ActionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.updated)
      * [`ActionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.user)
      * [`ActionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.user_id)
      * [`ActionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.workspace)
      * [`ActionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.action_schemas.ActionSchema.workspace_id)
  * [zenml.zen_stores.schemas.api_key_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.api_key_schemas)
    * [`APIKeySchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)
      * [`APIKeySchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.active)
      * [`APIKeySchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.created)
      * [`APIKeySchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.description)
      * [`APIKeySchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.from_request)
      * [`APIKeySchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.id)
      * [`APIKeySchema.internal_update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.internal_update)
      * [`APIKeySchema.key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.key)
      * [`APIKeySchema.last_login`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.last_login)
      * [`APIKeySchema.last_rotated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.last_rotated)
      * [`APIKeySchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.model_computed_fields)
      * [`APIKeySchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.model_config)
      * [`APIKeySchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.model_fields)
      * [`APIKeySchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.name)
      * [`APIKeySchema.previous_key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.previous_key)
      * [`APIKeySchema.retain_period`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.retain_period)
      * [`APIKeySchema.rotate()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.rotate)
      * [`APIKeySchema.service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.service_account)
      * [`APIKeySchema.service_account_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.service_account_id)
      * [`APIKeySchema.to_internal_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.to_internal_model)
      * [`APIKeySchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.to_model)
      * [`APIKeySchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.update)
      * [`APIKeySchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema.updated)
  * [zenml.zen_stores.schemas.artifact_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.artifact_schemas)
    * [`ArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)
      * [`ArtifactSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.created)
      * [`ArtifactSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.from_request)
      * [`ArtifactSchema.has_custom_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.has_custom_name)
      * [`ArtifactSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.id)
      * [`ArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.model_computed_fields)
      * [`ArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.model_config)
      * [`ArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.model_fields)
      * [`ArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.name)
      * [`ArtifactSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.tags)
      * [`ArtifactSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.to_model)
      * [`ArtifactSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.update)
      * [`ArtifactSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.updated)
      * [`ArtifactSchema.versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema.versions)
    * [`ArtifactVersionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)
      * [`ArtifactVersionSchema.artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.artifact)
      * [`ArtifactVersionSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.artifact_id)
      * [`ArtifactVersionSchema.artifact_store_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.artifact_store_id)
      * [`ArtifactVersionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.created)
      * [`ArtifactVersionSchema.data_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.data_type)
      * [`ArtifactVersionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.from_request)
      * [`ArtifactVersionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.id)
      * [`ArtifactVersionSchema.input_of_step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.input_of_step_runs)
      * [`ArtifactVersionSchema.materializer`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.materializer)
      * [`ArtifactVersionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.model_computed_fields)
      * [`ArtifactVersionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.model_config)
      * [`ArtifactVersionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.model_fields)
      * [`ArtifactVersionSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.model_versions_artifacts_links)
      * [`ArtifactVersionSchema.output_of_step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.output_of_step_runs)
      * [`ArtifactVersionSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.run_metadata)
      * [`ArtifactVersionSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.tags)
      * [`ArtifactVersionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.to_model)
      * [`ArtifactVersionSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.type)
      * [`ArtifactVersionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.update)
      * [`ArtifactVersionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.updated)
      * [`ArtifactVersionSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.uri)
      * [`ArtifactVersionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.user)
      * [`ArtifactVersionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.user_id)
      * [`ArtifactVersionSchema.version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.version)
      * [`ArtifactVersionSchema.version_number`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.version_number)
      * [`ArtifactVersionSchema.visualizations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.visualizations)
      * [`ArtifactVersionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.workspace)
      * [`ArtifactVersionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema.workspace_id)
  * [zenml.zen_stores.schemas.artifact_visualization_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.artifact_visualization_schemas)
    * [`ArtifactVisualizationSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema)
      * [`ArtifactVisualizationSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.artifact_version)
      * [`ArtifactVisualizationSchema.artifact_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.artifact_version_id)
      * [`ArtifactVisualizationSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.created)
      * [`ArtifactVisualizationSchema.from_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.from_model)
      * [`ArtifactVisualizationSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.id)
      * [`ArtifactVisualizationSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.model_computed_fields)
      * [`ArtifactVisualizationSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.model_config)
      * [`ArtifactVisualizationSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.model_fields)
      * [`ArtifactVisualizationSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.to_model)
      * [`ArtifactVisualizationSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.type)
      * [`ArtifactVisualizationSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.updated)
      * [`ArtifactVisualizationSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema.uri)
  * [zenml.zen_stores.schemas.base_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.base_schemas)
    * [`BaseSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema)
      * [`BaseSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.created)
      * [`BaseSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.id)
      * [`BaseSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.model_computed_fields)
      * [`BaseSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.model_config)
      * [`BaseSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.model_fields)
      * [`BaseSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.to_model)
      * [`BaseSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.BaseSchema.updated)
    * [`NamedSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.NamedSchema)
      * [`NamedSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.NamedSchema.model_computed_fields)
      * [`NamedSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.NamedSchema.model_config)
      * [`NamedSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.NamedSchema.model_fields)
      * [`NamedSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.base_schemas.NamedSchema.name)
  * [zenml.zen_stores.schemas.code_repository_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.code_repository_schemas)
    * [`CodeReferenceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema)
      * [`CodeReferenceSchema.code_repository`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.code_repository)
      * [`CodeReferenceSchema.code_repository_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.code_repository_id)
      * [`CodeReferenceSchema.commit`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.commit)
      * [`CodeReferenceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.created)
      * [`CodeReferenceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.from_request)
      * [`CodeReferenceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.id)
      * [`CodeReferenceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.model_computed_fields)
      * [`CodeReferenceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.model_config)
      * [`CodeReferenceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.model_fields)
      * [`CodeReferenceSchema.subdirectory`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.subdirectory)
      * [`CodeReferenceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.to_model)
      * [`CodeReferenceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.updated)
      * [`CodeReferenceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.workspace)
      * [`CodeReferenceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema.workspace_id)
    * [`CodeRepositorySchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)
      * [`CodeRepositorySchema.config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.config)
      * [`CodeRepositorySchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.created)
      * [`CodeRepositorySchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.description)
      * [`CodeRepositorySchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.from_request)
      * [`CodeRepositorySchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.id)
      * [`CodeRepositorySchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.logo_url)
      * [`CodeRepositorySchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.model_computed_fields)
      * [`CodeRepositorySchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.model_config)
      * [`CodeRepositorySchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.model_fields)
      * [`CodeRepositorySchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.name)
      * [`CodeRepositorySchema.source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.source)
      * [`CodeRepositorySchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.to_model)
      * [`CodeRepositorySchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.update)
      * [`CodeRepositorySchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.updated)
      * [`CodeRepositorySchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.user)
      * [`CodeRepositorySchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.user_id)
      * [`CodeRepositorySchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.workspace)
      * [`CodeRepositorySchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema.workspace_id)
  * [zenml.zen_stores.schemas.component_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.component_schemas)
    * [`StackComponentSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)
      * [`StackComponentSchema.component_spec_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.component_spec_path)
      * [`StackComponentSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.configuration)
      * [`StackComponentSchema.connector`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.connector)
      * [`StackComponentSchema.connector_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.connector_id)
      * [`StackComponentSchema.connector_resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.connector_resource_id)
      * [`StackComponentSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.created)
      * [`StackComponentSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.flavor)
      * [`StackComponentSchema.flavor_schema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.flavor_schema)
      * [`StackComponentSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.id)
      * [`StackComponentSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.labels)
      * [`StackComponentSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.model_computed_fields)
      * [`StackComponentSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.model_config)
      * [`StackComponentSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.model_fields)
      * [`StackComponentSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.name)
      * [`StackComponentSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.run_metadata)
      * [`StackComponentSchema.run_or_step_logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.run_or_step_logs)
      * [`StackComponentSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.schedules)
      * [`StackComponentSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.stacks)
      * [`StackComponentSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.to_model)
      * [`StackComponentSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.type)
      * [`StackComponentSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.update)
      * [`StackComponentSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.updated)
      * [`StackComponentSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.user)
      * [`StackComponentSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.user_id)
      * [`StackComponentSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.workspace)
      * [`StackComponentSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.component_schemas.StackComponentSchema.workspace_id)
  * [zenml.zen_stores.schemas.constants module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.constants)
  * [zenml.zen_stores.schemas.device_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.device_schemas)
    * [`OAuthDeviceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema)
      * [`OAuthDeviceSchema.city`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.city)
      * [`OAuthDeviceSchema.client_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.client_id)
      * [`OAuthDeviceSchema.country`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.country)
      * [`OAuthDeviceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.created)
      * [`OAuthDeviceSchema.device_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.device_code)
      * [`OAuthDeviceSchema.expires`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.expires)
      * [`OAuthDeviceSchema.failed_auth_attempts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.failed_auth_attempts)
      * [`OAuthDeviceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.from_request)
      * [`OAuthDeviceSchema.hostname`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.hostname)
      * [`OAuthDeviceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.id)
      * [`OAuthDeviceSchema.internal_update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.internal_update)
      * [`OAuthDeviceSchema.ip_address`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.ip_address)
      * [`OAuthDeviceSchema.last_login`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.last_login)
      * [`OAuthDeviceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.model_computed_fields)
      * [`OAuthDeviceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.model_config)
      * [`OAuthDeviceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.model_fields)
      * [`OAuthDeviceSchema.os`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.os)
      * [`OAuthDeviceSchema.python_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.python_version)
      * [`OAuthDeviceSchema.region`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.region)
      * [`OAuthDeviceSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.status)
      * [`OAuthDeviceSchema.to_internal_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.to_internal_model)
      * [`OAuthDeviceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.to_model)
      * [`OAuthDeviceSchema.trusted_device`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.trusted_device)
      * [`OAuthDeviceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.update)
      * [`OAuthDeviceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.updated)
      * [`OAuthDeviceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.user)
      * [`OAuthDeviceSchema.user_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.user_code)
      * [`OAuthDeviceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.user_id)
      * [`OAuthDeviceSchema.zenml_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema.zenml_version)
  * [zenml.zen_stores.schemas.event_source_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.event_source_schemas)
    * [`EventSourceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)
      * [`EventSourceSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.configuration)
      * [`EventSourceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.created)
      * [`EventSourceSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.description)
      * [`EventSourceSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.flavor)
      * [`EventSourceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.from_request)
      * [`EventSourceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.id)
      * [`EventSourceSchema.is_active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.is_active)
      * [`EventSourceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.model_computed_fields)
      * [`EventSourceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.model_config)
      * [`EventSourceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.model_fields)
      * [`EventSourceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.name)
      * [`EventSourceSchema.plugin_subtype`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.plugin_subtype)
      * [`EventSourceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.to_model)
      * [`EventSourceSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.triggers)
      * [`EventSourceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.update)
      * [`EventSourceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.updated)
      * [`EventSourceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.user)
      * [`EventSourceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.user_id)
      * [`EventSourceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.workspace)
      * [`EventSourceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema.workspace_id)
  * [zenml.zen_stores.schemas.flavor_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.flavor_schemas)
    * [`FlavorSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema)
      * [`FlavorSchema.config_schema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.config_schema)
      * [`FlavorSchema.connector_resource_id_attr`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.connector_resource_id_attr)
      * [`FlavorSchema.connector_resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.connector_resource_type)
      * [`FlavorSchema.connector_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.connector_type)
      * [`FlavorSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.created)
      * [`FlavorSchema.docs_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.docs_url)
      * [`FlavorSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.id)
      * [`FlavorSchema.integration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.integration)
      * [`FlavorSchema.is_custom`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.is_custom)
      * [`FlavorSchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.logo_url)
      * [`FlavorSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.model_computed_fields)
      * [`FlavorSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.model_config)
      * [`FlavorSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.model_fields)
      * [`FlavorSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.name)
      * [`FlavorSchema.sdk_docs_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.sdk_docs_url)
      * [`FlavorSchema.source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.source)
      * [`FlavorSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.to_model)
      * [`FlavorSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.type)
      * [`FlavorSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.update)
      * [`FlavorSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.updated)
      * [`FlavorSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.user)
      * [`FlavorSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.user_id)
      * [`FlavorSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.workspace)
      * [`FlavorSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema.workspace_id)
  * [zenml.zen_stores.schemas.logs_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.logs_schemas)
    * [`LogsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema)
      * [`LogsSchema.artifact_store`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.artifact_store)
      * [`LogsSchema.artifact_store_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.artifact_store_id)
      * [`LogsSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.created)
      * [`LogsSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.id)
      * [`LogsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.model_computed_fields)
      * [`LogsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.model_config)
      * [`LogsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.model_fields)
      * [`LogsSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.pipeline_run)
      * [`LogsSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.pipeline_run_id)
      * [`LogsSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.step_run)
      * [`LogsSchema.step_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.step_run_id)
      * [`LogsSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.to_model)
      * [`LogsSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.updated)
      * [`LogsSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.logs_schemas.LogsSchema.uri)
  * [zenml.zen_stores.schemas.model_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.model_schemas)
    * [`ModelSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema)
      * [`ModelSchema.artifact_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.artifact_links)
      * [`ModelSchema.audience`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.audience)
      * [`ModelSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.created)
      * [`ModelSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.description)
      * [`ModelSchema.ethics`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.ethics)
      * [`ModelSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.from_request)
      * [`ModelSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.id)
      * [`ModelSchema.license`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.license)
      * [`ModelSchema.limitations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.limitations)
      * [`ModelSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.model_computed_fields)
      * [`ModelSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.model_config)
      * [`ModelSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.model_fields)
      * [`ModelSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.model_versions)
      * [`ModelSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.name)
      * [`ModelSchema.pipeline_run_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.pipeline_run_links)
      * [`ModelSchema.save_models_to_registry`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.save_models_to_registry)
      * [`ModelSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.tags)
      * [`ModelSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.to_model)
      * [`ModelSchema.trade_offs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.trade_offs)
      * [`ModelSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.update)
      * [`ModelSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.updated)
      * [`ModelSchema.use_cases`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.use_cases)
      * [`ModelSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.user)
      * [`ModelSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.user_id)
      * [`ModelSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.workspace)
      * [`ModelSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelSchema.workspace_id)
    * [`ModelVersionArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)
      * [`ModelVersionArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.artifact_version)
      * [`ModelVersionArtifactSchema.artifact_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.artifact_version_id)
      * [`ModelVersionArtifactSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.created)
      * [`ModelVersionArtifactSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.from_request)
      * [`ModelVersionArtifactSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.id)
      * [`ModelVersionArtifactSchema.is_deployment_artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.is_deployment_artifact)
      * [`ModelVersionArtifactSchema.is_model_artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.is_model_artifact)
      * [`ModelVersionArtifactSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model)
      * [`ModelVersionArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_computed_fields)
      * [`ModelVersionArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_config)
      * [`ModelVersionArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_fields)
      * [`ModelVersionArtifactSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_id)
      * [`ModelVersionArtifactSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_version)
      * [`ModelVersionArtifactSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.model_version_id)
      * [`ModelVersionArtifactSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.to_model)
      * [`ModelVersionArtifactSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.updated)
      * [`ModelVersionArtifactSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.user)
      * [`ModelVersionArtifactSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.user_id)
      * [`ModelVersionArtifactSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.workspace)
      * [`ModelVersionArtifactSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema.workspace_id)
    * [`ModelVersionPipelineRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)
      * [`ModelVersionPipelineRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.created)
      * [`ModelVersionPipelineRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.from_request)
      * [`ModelVersionPipelineRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.id)
      * [`ModelVersionPipelineRunSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model)
      * [`ModelVersionPipelineRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_computed_fields)
      * [`ModelVersionPipelineRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_config)
      * [`ModelVersionPipelineRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_fields)
      * [`ModelVersionPipelineRunSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_id)
      * [`ModelVersionPipelineRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_version)
      * [`ModelVersionPipelineRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.model_version_id)
      * [`ModelVersionPipelineRunSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.pipeline_run)
      * [`ModelVersionPipelineRunSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.pipeline_run_id)
      * [`ModelVersionPipelineRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.to_model)
      * [`ModelVersionPipelineRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.updated)
      * [`ModelVersionPipelineRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.user)
      * [`ModelVersionPipelineRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.user_id)
      * [`ModelVersionPipelineRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.workspace)
      * [`ModelVersionPipelineRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema.workspace_id)
    * [`ModelVersionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)
      * [`ModelVersionSchema.artifact_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.artifact_links)
      * [`ModelVersionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.created)
      * [`ModelVersionSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.description)
      * [`ModelVersionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.from_request)
      * [`ModelVersionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.id)
      * [`ModelVersionSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.model)
      * [`ModelVersionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.model_computed_fields)
      * [`ModelVersionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.model_config)
      * [`ModelVersionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.model_fields)
      * [`ModelVersionSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.model_id)
      * [`ModelVersionSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.name)
      * [`ModelVersionSchema.number`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.number)
      * [`ModelVersionSchema.pipeline_run_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.pipeline_run_links)
      * [`ModelVersionSchema.pipeline_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.pipeline_runs)
      * [`ModelVersionSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.run_metadata)
      * [`ModelVersionSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.services)
      * [`ModelVersionSchema.stage`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.stage)
      * [`ModelVersionSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.step_runs)
      * [`ModelVersionSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.tags)
      * [`ModelVersionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.to_model)
      * [`ModelVersionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.update)
      * [`ModelVersionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.updated)
      * [`ModelVersionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.user)
      * [`ModelVersionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.user_id)
      * [`ModelVersionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.workspace)
      * [`ModelVersionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema.workspace_id)
  * [zenml.zen_stores.schemas.pipeline_build_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.pipeline_build_schemas)
    * [`PipelineBuildSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)
      * [`PipelineBuildSchema.checksum`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.checksum)
      * [`PipelineBuildSchema.contains_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.contains_code)
      * [`PipelineBuildSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.created)
      * [`PipelineBuildSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.from_request)
      * [`PipelineBuildSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.id)
      * [`PipelineBuildSchema.images`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.images)
      * [`PipelineBuildSchema.is_local`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.is_local)
      * [`PipelineBuildSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.model_computed_fields)
      * [`PipelineBuildSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.model_config)
      * [`PipelineBuildSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.model_fields)
      * [`PipelineBuildSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.pipeline)
      * [`PipelineBuildSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.pipeline_id)
      * [`PipelineBuildSchema.python_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.python_version)
      * [`PipelineBuildSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.stack)
      * [`PipelineBuildSchema.stack_checksum`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.stack_checksum)
      * [`PipelineBuildSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.stack_id)
      * [`PipelineBuildSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.to_model)
      * [`PipelineBuildSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.updated)
      * [`PipelineBuildSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.user)
      * [`PipelineBuildSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.user_id)
      * [`PipelineBuildSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.workspace)
      * [`PipelineBuildSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.workspace_id)
      * [`PipelineBuildSchema.zenml_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema.zenml_version)
  * [zenml.zen_stores.schemas.pipeline_deployment_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.pipeline_deployment_schemas)
    * [`PipelineDeploymentSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)
      * [`PipelineDeploymentSchema.build`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.build)
      * [`PipelineDeploymentSchema.build_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.build_id)
      * [`PipelineDeploymentSchema.client_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.client_environment)
      * [`PipelineDeploymentSchema.client_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.client_version)
      * [`PipelineDeploymentSchema.code_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.code_path)
      * [`PipelineDeploymentSchema.code_reference`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.code_reference)
      * [`PipelineDeploymentSchema.code_reference_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.code_reference_id)
      * [`PipelineDeploymentSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.created)
      * [`PipelineDeploymentSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.from_request)
      * [`PipelineDeploymentSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.id)
      * [`PipelineDeploymentSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.model_computed_fields)
      * [`PipelineDeploymentSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.model_config)
      * [`PipelineDeploymentSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.model_fields)
      * [`PipelineDeploymentSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline)
      * [`PipelineDeploymentSchema.pipeline_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline_configuration)
      * [`PipelineDeploymentSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline_id)
      * [`PipelineDeploymentSchema.pipeline_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline_runs)
      * [`PipelineDeploymentSchema.pipeline_spec`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline_spec)
      * [`PipelineDeploymentSchema.pipeline_version_hash`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.pipeline_version_hash)
      * [`PipelineDeploymentSchema.run_name_template`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.run_name_template)
      * [`PipelineDeploymentSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.schedule)
      * [`PipelineDeploymentSchema.schedule_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.schedule_id)
      * [`PipelineDeploymentSchema.server_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.server_version)
      * [`PipelineDeploymentSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.stack)
      * [`PipelineDeploymentSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.stack_id)
      * [`PipelineDeploymentSchema.step_configurations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.step_configurations)
      * [`PipelineDeploymentSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.step_runs)
      * [`PipelineDeploymentSchema.template_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.template_id)
      * [`PipelineDeploymentSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.to_model)
      * [`PipelineDeploymentSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.updated)
      * [`PipelineDeploymentSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.user)
      * [`PipelineDeploymentSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.user_id)
      * [`PipelineDeploymentSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.workspace)
      * [`PipelineDeploymentSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema.workspace_id)
  * [zenml.zen_stores.schemas.pipeline_run_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.pipeline_run_schemas)
    * [`PipelineRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)
      * [`PipelineRunSchema.build`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.build)
      * [`PipelineRunSchema.build_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.build_id)
      * [`PipelineRunSchema.client_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.client_environment)
      * [`PipelineRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.created)
      * [`PipelineRunSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.deployment)
      * [`PipelineRunSchema.deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.deployment_id)
      * [`PipelineRunSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.end_time)
      * [`PipelineRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.from_request)
      * [`PipelineRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.id)
      * [`PipelineRunSchema.logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.logs)
      * [`PipelineRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_computed_fields)
      * [`PipelineRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_config)
      * [`PipelineRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_fields)
      * [`PipelineRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_version)
      * [`PipelineRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_version_id)
      * [`PipelineRunSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.model_versions_pipeline_runs_links)
      * [`PipelineRunSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.name)
      * [`PipelineRunSchema.orchestrator_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.orchestrator_environment)
      * [`PipelineRunSchema.orchestrator_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.orchestrator_run_id)
      * [`PipelineRunSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.pipeline)
      * [`PipelineRunSchema.pipeline_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.pipeline_configuration)
      * [`PipelineRunSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.pipeline_id)
      * [`PipelineRunSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.run_metadata)
      * [`PipelineRunSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.schedule)
      * [`PipelineRunSchema.schedule_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.schedule_id)
      * [`PipelineRunSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.services)
      * [`PipelineRunSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.stack)
      * [`PipelineRunSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.stack_id)
      * [`PipelineRunSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.start_time)
      * [`PipelineRunSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.status)
      * [`PipelineRunSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.step_runs)
      * [`PipelineRunSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.tags)
      * [`PipelineRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.to_model)
      * [`PipelineRunSchema.trigger_execution`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.trigger_execution)
      * [`PipelineRunSchema.trigger_execution_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.trigger_execution_id)
      * [`PipelineRunSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.update)
      * [`PipelineRunSchema.update_placeholder()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.update_placeholder)
      * [`PipelineRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.updated)
      * [`PipelineRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.user)
      * [`PipelineRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.user_id)
      * [`PipelineRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.workspace)
      * [`PipelineRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema.workspace_id)
  * [zenml.zen_stores.schemas.pipeline_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.pipeline_schemas)
    * [`PipelineSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)
      * [`PipelineSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.builds)
      * [`PipelineSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.created)
      * [`PipelineSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.deployments)
      * [`PipelineSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.description)
      * [`PipelineSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.from_request)
      * [`PipelineSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.id)
      * [`PipelineSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.model_computed_fields)
      * [`PipelineSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.model_config)
      * [`PipelineSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.model_fields)
      * [`PipelineSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.name)
      * [`PipelineSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.runs)
      * [`PipelineSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.schedules)
      * [`PipelineSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.tags)
      * [`PipelineSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.to_model)
      * [`PipelineSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.update)
      * [`PipelineSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.updated)
      * [`PipelineSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.user)
      * [`PipelineSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.user_id)
      * [`PipelineSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.workspace)
      * [`PipelineSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema.workspace_id)
  * [zenml.zen_stores.schemas.run_metadata_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.run_metadata_schemas)
    * [`RunMetadataSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)
      * [`RunMetadataSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.artifact_version)
      * [`RunMetadataSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.created)
      * [`RunMetadataSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.id)
      * [`RunMetadataSchema.key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.key)
      * [`RunMetadataSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.model_computed_fields)
      * [`RunMetadataSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.model_config)
      * [`RunMetadataSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.model_fields)
      * [`RunMetadataSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.model_version)
      * [`RunMetadataSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.pipeline_run)
      * [`RunMetadataSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.resource_id)
      * [`RunMetadataSchema.resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.resource_type)
      * [`RunMetadataSchema.stack_component`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.stack_component)
      * [`RunMetadataSchema.stack_component_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.stack_component_id)
      * [`RunMetadataSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.step_run)
      * [`RunMetadataSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.to_model)
      * [`RunMetadataSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.type)
      * [`RunMetadataSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.updated)
      * [`RunMetadataSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.user)
      * [`RunMetadataSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.user_id)
      * [`RunMetadataSchema.value`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.value)
      * [`RunMetadataSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.workspace)
      * [`RunMetadataSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema.workspace_id)
  * [zenml.zen_stores.schemas.run_template_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.run_template_schemas)
    * [`RunTemplateSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema)
      * [`RunTemplateSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.created)
      * [`RunTemplateSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.description)
      * [`RunTemplateSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.from_request)
      * [`RunTemplateSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.id)
      * [`RunTemplateSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.model_computed_fields)
      * [`RunTemplateSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.model_config)
      * [`RunTemplateSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.model_fields)
      * [`RunTemplateSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.name)
      * [`RunTemplateSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.runs)
      * [`RunTemplateSchema.source_deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.source_deployment)
      * [`RunTemplateSchema.source_deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.source_deployment_id)
      * [`RunTemplateSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.tags)
      * [`RunTemplateSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.to_model)
      * [`RunTemplateSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.update)
      * [`RunTemplateSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.updated)
      * [`RunTemplateSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.user)
      * [`RunTemplateSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.user_id)
      * [`RunTemplateSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.workspace)
      * [`RunTemplateSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema.workspace_id)
  * [zenml.zen_stores.schemas.schedule_schema module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.schedule_schema)
    * [`ScheduleSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)
      * [`ScheduleSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.active)
      * [`ScheduleSchema.catchup`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.catchup)
      * [`ScheduleSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.created)
      * [`ScheduleSchema.cron_expression`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.cron_expression)
      * [`ScheduleSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.deployment)
      * [`ScheduleSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.end_time)
      * [`ScheduleSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.from_request)
      * [`ScheduleSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.id)
      * [`ScheduleSchema.interval_second`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.interval_second)
      * [`ScheduleSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.model_computed_fields)
      * [`ScheduleSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.model_config)
      * [`ScheduleSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.model_fields)
      * [`ScheduleSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.name)
      * [`ScheduleSchema.orchestrator`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.orchestrator)
      * [`ScheduleSchema.orchestrator_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.orchestrator_id)
      * [`ScheduleSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.pipeline)
      * [`ScheduleSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.pipeline_id)
      * [`ScheduleSchema.run_once_start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.run_once_start_time)
      * [`ScheduleSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.start_time)
      * [`ScheduleSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.to_model)
      * [`ScheduleSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.update)
      * [`ScheduleSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.updated)
      * [`ScheduleSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.user)
      * [`ScheduleSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.user_id)
      * [`ScheduleSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.workspace)
      * [`ScheduleSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema.workspace_id)
  * [zenml.zen_stores.schemas.schema_utils module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.schema_utils)
    * [`build_foreign_key_field()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schema_utils.build_foreign_key_field)
    * [`foreign_key_constraint_name()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.schema_utils.foreign_key_constraint_name)
  * [zenml.zen_stores.schemas.secret_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.secret_schemas)
    * [`SecretDecodeError`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretDecodeError)
    * [`SecretSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema)
      * [`SecretSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.created)
      * [`SecretSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.from_request)
      * [`SecretSchema.get_secret_values()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.get_secret_values)
      * [`SecretSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.id)
      * [`SecretSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.model_computed_fields)
      * [`SecretSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.model_config)
      * [`SecretSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.model_fields)
      * [`SecretSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.name)
      * [`SecretSchema.scope`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.scope)
      * [`SecretSchema.set_secret_values()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.set_secret_values)
      * [`SecretSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.to_model)
      * [`SecretSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.update)
      * [`SecretSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.updated)
      * [`SecretSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.user)
      * [`SecretSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.user_id)
      * [`SecretSchema.values`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.values)
      * [`SecretSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.workspace)
      * [`SecretSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.secret_schemas.SecretSchema.workspace_id)
  * [zenml.zen_stores.schemas.server_settings_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.server_settings_schemas)
    * [`ServerSettingsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema)
      * [`ServerSettingsSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.active)
      * [`ServerSettingsSchema.display_announcements`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.display_announcements)
      * [`ServerSettingsSchema.display_updates`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.display_updates)
      * [`ServerSettingsSchema.enable_analytics`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.enable_analytics)
      * [`ServerSettingsSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.id)
      * [`ServerSettingsSchema.last_user_activity`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.last_user_activity)
      * [`ServerSettingsSchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.logo_url)
      * [`ServerSettingsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.model_computed_fields)
      * [`ServerSettingsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.model_config)
      * [`ServerSettingsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.model_fields)
      * [`ServerSettingsSchema.onboarding_state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.onboarding_state)
      * [`ServerSettingsSchema.server_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.server_name)
      * [`ServerSettingsSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.to_model)
      * [`ServerSettingsSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.update)
      * [`ServerSettingsSchema.update_onboarding_state()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.update_onboarding_state)
      * [`ServerSettingsSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema.updated)
  * [zenml.zen_stores.schemas.service_connector_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.service_connector_schemas)
    * [`ServiceConnectorSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)
      * [`ServiceConnectorSchema.auth_method`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.auth_method)
      * [`ServiceConnectorSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.components)
      * [`ServiceConnectorSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.configuration)
      * [`ServiceConnectorSchema.connector_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.connector_type)
      * [`ServiceConnectorSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.created)
      * [`ServiceConnectorSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.description)
      * [`ServiceConnectorSchema.expiration_seconds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.expiration_seconds)
      * [`ServiceConnectorSchema.expires_at`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.expires_at)
      * [`ServiceConnectorSchema.expires_skew_tolerance`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.expires_skew_tolerance)
      * [`ServiceConnectorSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.from_request)
      * [`ServiceConnectorSchema.has_labels()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.has_labels)
      * [`ServiceConnectorSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.id)
      * [`ServiceConnectorSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.labels)
      * [`ServiceConnectorSchema.labels_dict`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.labels_dict)
      * [`ServiceConnectorSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.model_computed_fields)
      * [`ServiceConnectorSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.model_config)
      * [`ServiceConnectorSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.model_fields)
      * [`ServiceConnectorSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.name)
      * [`ServiceConnectorSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.resource_id)
      * [`ServiceConnectorSchema.resource_types`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.resource_types)
      * [`ServiceConnectorSchema.resource_types_list`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.resource_types_list)
      * [`ServiceConnectorSchema.secret_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.secret_id)
      * [`ServiceConnectorSchema.supports_instances`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.supports_instances)
      * [`ServiceConnectorSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.to_model)
      * [`ServiceConnectorSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.update)
      * [`ServiceConnectorSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.updated)
      * [`ServiceConnectorSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.user)
      * [`ServiceConnectorSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.user_id)
      * [`ServiceConnectorSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.workspace)
      * [`ServiceConnectorSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema.workspace_id)
  * [zenml.zen_stores.schemas.service_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.service_schemas)
    * [`ServiceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema)
      * [`ServiceSchema.admin_state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.admin_state)
      * [`ServiceSchema.config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.config)
      * [`ServiceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.created)
      * [`ServiceSchema.endpoint`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.endpoint)
      * [`ServiceSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.flavor)
      * [`ServiceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.from_request)
      * [`ServiceSchema.health_check_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.health_check_url)
      * [`ServiceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.id)
      * [`ServiceSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.labels)
      * [`ServiceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.model_computed_fields)
      * [`ServiceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.model_config)
      * [`ServiceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.model_fields)
      * [`ServiceSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.model_version)
      * [`ServiceSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.model_version_id)
      * [`ServiceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.name)
      * [`ServiceSchema.pipeline_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.pipeline_name)
      * [`ServiceSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.pipeline_run)
      * [`ServiceSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.pipeline_run_id)
      * [`ServiceSchema.pipeline_step_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.pipeline_step_name)
      * [`ServiceSchema.prediction_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.prediction_url)
      * [`ServiceSchema.service_source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.service_source)
      * [`ServiceSchema.service_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.service_type)
      * [`ServiceSchema.state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.state)
      * [`ServiceSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.status)
      * [`ServiceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.to_model)
      * [`ServiceSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.type)
      * [`ServiceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.update)
      * [`ServiceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.updated)
      * [`ServiceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.user)
      * [`ServiceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.user_id)
      * [`ServiceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.workspace)
      * [`ServiceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.service_schemas.ServiceSchema.workspace_id)
  * [zenml.zen_stores.schemas.stack_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.stack_schemas)
    * [`StackCompositionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema)
      * [`StackCompositionSchema.component_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema.component_id)
      * [`StackCompositionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema.model_computed_fields)
      * [`StackCompositionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema.model_config)
      * [`StackCompositionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema.model_fields)
      * [`StackCompositionSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema.stack_id)
    * [`StackSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema)
      * [`StackSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.builds)
      * [`StackSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.components)
      * [`StackSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.created)
      * [`StackSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.deployments)
      * [`StackSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.id)
      * [`StackSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.labels)
      * [`StackSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.model_computed_fields)
      * [`StackSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.model_config)
      * [`StackSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.model_fields)
      * [`StackSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.name)
      * [`StackSchema.stack_spec_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.stack_spec_path)
      * [`StackSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.to_model)
      * [`StackSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.update)
      * [`StackSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.updated)
      * [`StackSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.user)
      * [`StackSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.user_id)
      * [`StackSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.workspace)
      * [`StackSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.stack_schemas.StackSchema.workspace_id)
  * [zenml.zen_stores.schemas.step_run_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.step_run_schemas)
    * [`StepRunInputArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema)
      * [`StepRunInputArtifactSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.artifact_id)
      * [`StepRunInputArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.artifact_version)
      * [`StepRunInputArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.model_computed_fields)
      * [`StepRunInputArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.model_config)
      * [`StepRunInputArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.model_fields)
      * [`StepRunInputArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.name)
      * [`StepRunInputArtifactSchema.step_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.step_id)
      * [`StepRunInputArtifactSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.step_run)
      * [`StepRunInputArtifactSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema.type)
    * [`StepRunOutputArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema)
      * [`StepRunOutputArtifactSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.artifact_id)
      * [`StepRunOutputArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.artifact_version)
      * [`StepRunOutputArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.model_computed_fields)
      * [`StepRunOutputArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.model_config)
      * [`StepRunOutputArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.model_fields)
      * [`StepRunOutputArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.name)
      * [`StepRunOutputArtifactSchema.step_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.step_id)
      * [`StepRunOutputArtifactSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.step_run)
      * [`StepRunOutputArtifactSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema.type)
    * [`StepRunParentsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema)
      * [`StepRunParentsSchema.child_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema.child_id)
      * [`StepRunParentsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema.model_computed_fields)
      * [`StepRunParentsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema.model_config)
      * [`StepRunParentsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema.model_fields)
      * [`StepRunParentsSchema.parent_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema.parent_id)
    * [`StepRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)
      * [`StepRunSchema.cache_key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.cache_key)
      * [`StepRunSchema.code_hash`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.code_hash)
      * [`StepRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.created)
      * [`StepRunSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.deployment)
      * [`StepRunSchema.deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.deployment_id)
      * [`StepRunSchema.docstring`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.docstring)
      * [`StepRunSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.end_time)
      * [`StepRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.from_request)
      * [`StepRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.id)
      * [`StepRunSchema.input_artifacts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.input_artifacts)
      * [`StepRunSchema.logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.logs)
      * [`StepRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.model_computed_fields)
      * [`StepRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.model_config)
      * [`StepRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.model_fields)
      * [`StepRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.model_version)
      * [`StepRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.model_version_id)
      * [`StepRunSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.name)
      * [`StepRunSchema.original_step_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.original_step_run_id)
      * [`StepRunSchema.output_artifacts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.output_artifacts)
      * [`StepRunSchema.parents`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.parents)
      * [`StepRunSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.pipeline_run_id)
      * [`StepRunSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.run_metadata)
      * [`StepRunSchema.source_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.source_code)
      * [`StepRunSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.start_time)
      * [`StepRunSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.status)
      * [`StepRunSchema.step_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.step_configuration)
      * [`StepRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.to_model)
      * [`StepRunSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.update)
      * [`StepRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.updated)
      * [`StepRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.user)
      * [`StepRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.user_id)
      * [`StepRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.workspace)
      * [`StepRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema.workspace_id)
  * [zenml.zen_stores.schemas.tag_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.tag_schemas)
    * [`TagResourceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)
      * [`TagResourceSchema.artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.artifact)
      * [`TagResourceSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.artifact_version)
      * [`TagResourceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.created)
      * [`TagResourceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.from_request)
      * [`TagResourceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.id)
      * [`TagResourceSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.model)
      * [`TagResourceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.model_computed_fields)
      * [`TagResourceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.model_config)
      * [`TagResourceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.model_fields)
      * [`TagResourceSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.model_version)
      * [`TagResourceSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.resource_id)
      * [`TagResourceSchema.resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.resource_type)
      * [`TagResourceSchema.tag`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.tag)
      * [`TagResourceSchema.tag_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.tag_id)
      * [`TagResourceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.to_model)
      * [`TagResourceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema.updated)
    * [`TagSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema)
      * [`TagSchema.color`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.color)
      * [`TagSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.created)
      * [`TagSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.from_request)
      * [`TagSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.id)
      * [`TagSchema.links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.links)
      * [`TagSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.model_computed_fields)
      * [`TagSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.model_config)
      * [`TagSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.model_fields)
      * [`TagSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.name)
      * [`TagSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.to_model)
      * [`TagSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.update)
      * [`TagSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.tag_schemas.TagSchema.updated)
  * [zenml.zen_stores.schemas.trigger_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.trigger_schemas)
    * [`TriggerExecutionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema)
      * [`TriggerExecutionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.created)
      * [`TriggerExecutionSchema.event_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.event_metadata)
      * [`TriggerExecutionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.from_request)
      * [`TriggerExecutionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.id)
      * [`TriggerExecutionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.model_computed_fields)
      * [`TriggerExecutionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.model_config)
      * [`TriggerExecutionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.model_fields)
      * [`TriggerExecutionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.to_model)
      * [`TriggerExecutionSchema.trigger`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.trigger)
      * [`TriggerExecutionSchema.trigger_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.trigger_id)
      * [`TriggerExecutionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema.updated)
    * [`TriggerSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)
      * [`TriggerSchema.action`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.action)
      * [`TriggerSchema.action_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.action_id)
      * [`TriggerSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.created)
      * [`TriggerSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.description)
      * [`TriggerSchema.event_filter`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.event_filter)
      * [`TriggerSchema.event_source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.event_source)
      * [`TriggerSchema.event_source_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.event_source_id)
      * [`TriggerSchema.executions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.executions)
      * [`TriggerSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.from_request)
      * [`TriggerSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.id)
      * [`TriggerSchema.is_active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.is_active)
      * [`TriggerSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.model_computed_fields)
      * [`TriggerSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.model_config)
      * [`TriggerSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.model_fields)
      * [`TriggerSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.name)
      * [`TriggerSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.schedule)
      * [`TriggerSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.to_model)
      * [`TriggerSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.update)
      * [`TriggerSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.updated)
      * [`TriggerSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.user)
      * [`TriggerSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.user_id)
      * [`TriggerSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.workspace)
      * [`TriggerSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema.workspace_id)
  * [zenml.zen_stores.schemas.user_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.user_schemas)
    * [`UserSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema)
      * [`UserSchema.actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.actions)
      * [`UserSchema.activation_token`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.activation_token)
      * [`UserSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.active)
      * [`UserSchema.api_keys`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.api_keys)
      * [`UserSchema.artifact_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.artifact_versions)
      * [`UserSchema.auth_actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.auth_actions)
      * [`UserSchema.auth_devices`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.auth_devices)
      * [`UserSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.builds)
      * [`UserSchema.code_repositories`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.code_repositories)
      * [`UserSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.components)
      * [`UserSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.created)
      * [`UserSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.deployments)
      * [`UserSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.description)
      * [`UserSchema.email`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.email)
      * [`UserSchema.email_opted_in`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.email_opted_in)
      * [`UserSchema.event_sources`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.event_sources)
      * [`UserSchema.external_user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.external_user_id)
      * [`UserSchema.flavors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.flavors)
      * [`UserSchema.from_service_account_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.from_service_account_request)
      * [`UserSchema.from_user_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.from_user_request)
      * [`UserSchema.full_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.full_name)
      * [`UserSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.id)
      * [`UserSchema.is_admin`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.is_admin)
      * [`UserSchema.is_service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.is_service_account)
      * [`UserSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_computed_fields)
      * [`UserSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_config)
      * [`UserSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_fields)
      * [`UserSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_versions)
      * [`UserSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_versions_artifacts_links)
      * [`UserSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.model_versions_pipeline_runs_links)
      * [`UserSchema.models`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.models)
      * [`UserSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.name)
      * [`UserSchema.password`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.password)
      * [`UserSchema.pipelines`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.pipelines)
      * [`UserSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.run_metadata)
      * [`UserSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.runs)
      * [`UserSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.schedules)
      * [`UserSchema.secrets`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.secrets)
      * [`UserSchema.service_connectors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.service_connectors)
      * [`UserSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.services)
      * [`UserSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.stacks)
      * [`UserSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.step_runs)
      * [`UserSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.to_model)
      * [`UserSchema.to_service_account_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.to_service_account_model)
      * [`UserSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.triggers)
      * [`UserSchema.update_service_account()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.update_service_account)
      * [`UserSchema.update_user()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.update_user)
      * [`UserSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.updated)
      * [`UserSchema.user_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.user_schemas.UserSchema.user_metadata)
  * [zenml.zen_stores.schemas.utils module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.utils)
    * [`get_page_from_list()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.utils.get_page_from_list)
  * [zenml.zen_stores.schemas.workspace_schemas module](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas.workspace_schemas)
    * [`WorkspaceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)
      * [`WorkspaceSchema.actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.actions)
      * [`WorkspaceSchema.artifact_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.artifact_versions)
      * [`WorkspaceSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.builds)
      * [`WorkspaceSchema.code_repositories`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.code_repositories)
      * [`WorkspaceSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.components)
      * [`WorkspaceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.created)
      * [`WorkspaceSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.deployments)
      * [`WorkspaceSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.description)
      * [`WorkspaceSchema.event_sources`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.event_sources)
      * [`WorkspaceSchema.flavors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.flavors)
      * [`WorkspaceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.from_request)
      * [`WorkspaceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.id)
      * [`WorkspaceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_computed_fields)
      * [`WorkspaceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_config)
      * [`WorkspaceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_fields)
      * [`WorkspaceSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_versions)
      * [`WorkspaceSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_versions_artifacts_links)
      * [`WorkspaceSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.model_versions_pipeline_runs_links)
      * [`WorkspaceSchema.models`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.models)
      * [`WorkspaceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.name)
      * [`WorkspaceSchema.pipelines`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.pipelines)
      * [`WorkspaceSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.run_metadata)
      * [`WorkspaceSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.runs)
      * [`WorkspaceSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.schedules)
      * [`WorkspaceSchema.secrets`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.secrets)
      * [`WorkspaceSchema.service_connectors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.service_connectors)
      * [`WorkspaceSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.services)
      * [`WorkspaceSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.stacks)
      * [`WorkspaceSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.step_runs)
      * [`WorkspaceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.to_model)
      * [`WorkspaceSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.triggers)
      * [`WorkspaceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.update)
      * [`WorkspaceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema.updated)
  * [Module contents](zenml.zen_stores.schemas.md#module-zenml.zen_stores.schemas)
    * [`APIKeySchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema)
      * [`APIKeySchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.active)
      * [`APIKeySchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.created)
      * [`APIKeySchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.description)
      * [`APIKeySchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.from_request)
      * [`APIKeySchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.id)
      * [`APIKeySchema.internal_update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.internal_update)
      * [`APIKeySchema.key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.key)
      * [`APIKeySchema.last_login`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.last_login)
      * [`APIKeySchema.last_rotated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.last_rotated)
      * [`APIKeySchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.model_computed_fields)
      * [`APIKeySchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.model_config)
      * [`APIKeySchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.model_fields)
      * [`APIKeySchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.name)
      * [`APIKeySchema.previous_key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.previous_key)
      * [`APIKeySchema.retain_period`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.retain_period)
      * [`APIKeySchema.rotate()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.rotate)
      * [`APIKeySchema.service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.service_account)
      * [`APIKeySchema.service_account_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.service_account_id)
      * [`APIKeySchema.to_internal_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.to_internal_model)
      * [`APIKeySchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.to_model)
      * [`APIKeySchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.update)
      * [`APIKeySchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.APIKeySchema.updated)
    * [`ActionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema)
      * [`ActionSchema.auth_window`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.auth_window)
      * [`ActionSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.configuration)
      * [`ActionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.created)
      * [`ActionSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.description)
      * [`ActionSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.flavor)
      * [`ActionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.from_request)
      * [`ActionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.id)
      * [`ActionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.model_computed_fields)
      * [`ActionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.model_config)
      * [`ActionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.model_fields)
      * [`ActionSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.name)
      * [`ActionSchema.plugin_subtype`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.plugin_subtype)
      * [`ActionSchema.service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.service_account)
      * [`ActionSchema.service_account_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.service_account_id)
      * [`ActionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.to_model)
      * [`ActionSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.triggers)
      * [`ActionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.update)
      * [`ActionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.updated)
      * [`ActionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.user)
      * [`ActionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.user_id)
      * [`ActionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.workspace)
      * [`ActionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ActionSchema.workspace_id)
    * [`ArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema)
      * [`ArtifactSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.created)
      * [`ArtifactSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.from_request)
      * [`ArtifactSchema.has_custom_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.has_custom_name)
      * [`ArtifactSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.id)
      * [`ArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.model_computed_fields)
      * [`ArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.model_config)
      * [`ArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.model_fields)
      * [`ArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.name)
      * [`ArtifactSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.tags)
      * [`ArtifactSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.to_model)
      * [`ArtifactSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.update)
      * [`ArtifactSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.updated)
      * [`ArtifactSchema.versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactSchema.versions)
    * [`ArtifactVersionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema)
      * [`ArtifactVersionSchema.artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.artifact)
      * [`ArtifactVersionSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.artifact_id)
      * [`ArtifactVersionSchema.artifact_store_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.artifact_store_id)
      * [`ArtifactVersionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.created)
      * [`ArtifactVersionSchema.data_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.data_type)
      * [`ArtifactVersionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.from_request)
      * [`ArtifactVersionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.id)
      * [`ArtifactVersionSchema.input_of_step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.input_of_step_runs)
      * [`ArtifactVersionSchema.materializer`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.materializer)
      * [`ArtifactVersionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.model_computed_fields)
      * [`ArtifactVersionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.model_config)
      * [`ArtifactVersionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.model_fields)
      * [`ArtifactVersionSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.model_versions_artifacts_links)
      * [`ArtifactVersionSchema.output_of_step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.output_of_step_runs)
      * [`ArtifactVersionSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.run_metadata)
      * [`ArtifactVersionSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.tags)
      * [`ArtifactVersionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.to_model)
      * [`ArtifactVersionSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.type)
      * [`ArtifactVersionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.update)
      * [`ArtifactVersionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.updated)
      * [`ArtifactVersionSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.uri)
      * [`ArtifactVersionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.user)
      * [`ArtifactVersionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.user_id)
      * [`ArtifactVersionSchema.version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.version)
      * [`ArtifactVersionSchema.version_number`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.version_number)
      * [`ArtifactVersionSchema.visualizations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.visualizations)
      * [`ArtifactVersionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.workspace)
      * [`ArtifactVersionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVersionSchema.workspace_id)
    * [`ArtifactVisualizationSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema)
      * [`ArtifactVisualizationSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.artifact_version)
      * [`ArtifactVisualizationSchema.artifact_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.artifact_version_id)
      * [`ArtifactVisualizationSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.created)
      * [`ArtifactVisualizationSchema.from_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.from_model)
      * [`ArtifactVisualizationSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.id)
      * [`ArtifactVisualizationSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.model_computed_fields)
      * [`ArtifactVisualizationSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.model_config)
      * [`ArtifactVisualizationSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.model_fields)
      * [`ArtifactVisualizationSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.to_model)
      * [`ArtifactVisualizationSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.type)
      * [`ArtifactVisualizationSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.updated)
      * [`ArtifactVisualizationSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ArtifactVisualizationSchema.uri)
    * [`BaseSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema)
      * [`BaseSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.created)
      * [`BaseSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.id)
      * [`BaseSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.model_computed_fields)
      * [`BaseSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.model_config)
      * [`BaseSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.model_fields)
      * [`BaseSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.to_model)
      * [`BaseSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.BaseSchema.updated)
    * [`CodeReferenceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema)
      * [`CodeReferenceSchema.code_repository`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.code_repository)
      * [`CodeReferenceSchema.code_repository_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.code_repository_id)
      * [`CodeReferenceSchema.commit`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.commit)
      * [`CodeReferenceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.created)
      * [`CodeReferenceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.from_request)
      * [`CodeReferenceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.id)
      * [`CodeReferenceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.model_computed_fields)
      * [`CodeReferenceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.model_config)
      * [`CodeReferenceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.model_fields)
      * [`CodeReferenceSchema.subdirectory`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.subdirectory)
      * [`CodeReferenceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.to_model)
      * [`CodeReferenceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.updated)
      * [`CodeReferenceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.workspace)
      * [`CodeReferenceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeReferenceSchema.workspace_id)
    * [`CodeRepositorySchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema)
      * [`CodeRepositorySchema.config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.config)
      * [`CodeRepositorySchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.created)
      * [`CodeRepositorySchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.description)
      * [`CodeRepositorySchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.from_request)
      * [`CodeRepositorySchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.id)
      * [`CodeRepositorySchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.logo_url)
      * [`CodeRepositorySchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.model_computed_fields)
      * [`CodeRepositorySchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.model_config)
      * [`CodeRepositorySchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.model_fields)
      * [`CodeRepositorySchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.name)
      * [`CodeRepositorySchema.source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.source)
      * [`CodeRepositorySchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.to_model)
      * [`CodeRepositorySchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.update)
      * [`CodeRepositorySchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.updated)
      * [`CodeRepositorySchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.user)
      * [`CodeRepositorySchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.user_id)
      * [`CodeRepositorySchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.workspace)
      * [`CodeRepositorySchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.CodeRepositorySchema.workspace_id)
    * [`EventSourceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema)
      * [`EventSourceSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.configuration)
      * [`EventSourceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.created)
      * [`EventSourceSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.description)
      * [`EventSourceSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.flavor)
      * [`EventSourceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.from_request)
      * [`EventSourceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.id)
      * [`EventSourceSchema.is_active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.is_active)
      * [`EventSourceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.model_computed_fields)
      * [`EventSourceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.model_config)
      * [`EventSourceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.model_fields)
      * [`EventSourceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.name)
      * [`EventSourceSchema.plugin_subtype`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.plugin_subtype)
      * [`EventSourceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.to_model)
      * [`EventSourceSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.triggers)
      * [`EventSourceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.update)
      * [`EventSourceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.updated)
      * [`EventSourceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.user)
      * [`EventSourceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.user_id)
      * [`EventSourceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.workspace)
      * [`EventSourceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.EventSourceSchema.workspace_id)
    * [`FlavorSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema)
      * [`FlavorSchema.config_schema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.config_schema)
      * [`FlavorSchema.connector_resource_id_attr`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.connector_resource_id_attr)
      * [`FlavorSchema.connector_resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.connector_resource_type)
      * [`FlavorSchema.connector_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.connector_type)
      * [`FlavorSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.created)
      * [`FlavorSchema.docs_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.docs_url)
      * [`FlavorSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.id)
      * [`FlavorSchema.integration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.integration)
      * [`FlavorSchema.is_custom`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.is_custom)
      * [`FlavorSchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.logo_url)
      * [`FlavorSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.model_computed_fields)
      * [`FlavorSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.model_config)
      * [`FlavorSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.model_fields)
      * [`FlavorSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.name)
      * [`FlavorSchema.sdk_docs_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.sdk_docs_url)
      * [`FlavorSchema.source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.source)
      * [`FlavorSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.to_model)
      * [`FlavorSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.type)
      * [`FlavorSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.update)
      * [`FlavorSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.updated)
      * [`FlavorSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.user)
      * [`FlavorSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.user_id)
      * [`FlavorSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.workspace)
      * [`FlavorSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.FlavorSchema.workspace_id)
    * [`LogsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema)
      * [`LogsSchema.artifact_store`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.artifact_store)
      * [`LogsSchema.artifact_store_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.artifact_store_id)
      * [`LogsSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.created)
      * [`LogsSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.id)
      * [`LogsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.model_computed_fields)
      * [`LogsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.model_config)
      * [`LogsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.model_fields)
      * [`LogsSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.pipeline_run)
      * [`LogsSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.pipeline_run_id)
      * [`LogsSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.step_run)
      * [`LogsSchema.step_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.step_run_id)
      * [`LogsSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.to_model)
      * [`LogsSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.updated)
      * [`LogsSchema.uri`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.LogsSchema.uri)
    * [`ModelSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema)
      * [`ModelSchema.artifact_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.artifact_links)
      * [`ModelSchema.audience`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.audience)
      * [`ModelSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.created)
      * [`ModelSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.description)
      * [`ModelSchema.ethics`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.ethics)
      * [`ModelSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.from_request)
      * [`ModelSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.id)
      * [`ModelSchema.license`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.license)
      * [`ModelSchema.limitations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.limitations)
      * [`ModelSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.model_computed_fields)
      * [`ModelSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.model_config)
      * [`ModelSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.model_fields)
      * [`ModelSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.model_versions)
      * [`ModelSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.name)
      * [`ModelSchema.pipeline_run_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.pipeline_run_links)
      * [`ModelSchema.save_models_to_registry`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.save_models_to_registry)
      * [`ModelSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.tags)
      * [`ModelSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.to_model)
      * [`ModelSchema.trade_offs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.trade_offs)
      * [`ModelSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.update)
      * [`ModelSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.updated)
      * [`ModelSchema.use_cases`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.use_cases)
      * [`ModelSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.user)
      * [`ModelSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.user_id)
      * [`ModelSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.workspace)
      * [`ModelSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelSchema.workspace_id)
    * [`ModelVersionArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema)
      * [`ModelVersionArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.artifact_version)
      * [`ModelVersionArtifactSchema.artifact_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.artifact_version_id)
      * [`ModelVersionArtifactSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.created)
      * [`ModelVersionArtifactSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.from_request)
      * [`ModelVersionArtifactSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.id)
      * [`ModelVersionArtifactSchema.is_deployment_artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.is_deployment_artifact)
      * [`ModelVersionArtifactSchema.is_model_artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.is_model_artifact)
      * [`ModelVersionArtifactSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model)
      * [`ModelVersionArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_computed_fields)
      * [`ModelVersionArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_config)
      * [`ModelVersionArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_fields)
      * [`ModelVersionArtifactSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_id)
      * [`ModelVersionArtifactSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_version)
      * [`ModelVersionArtifactSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.model_version_id)
      * [`ModelVersionArtifactSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.to_model)
      * [`ModelVersionArtifactSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.updated)
      * [`ModelVersionArtifactSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.user)
      * [`ModelVersionArtifactSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.user_id)
      * [`ModelVersionArtifactSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.workspace)
      * [`ModelVersionArtifactSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionArtifactSchema.workspace_id)
    * [`ModelVersionPipelineRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)
      * [`ModelVersionPipelineRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.created)
      * [`ModelVersionPipelineRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.from_request)
      * [`ModelVersionPipelineRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.id)
      * [`ModelVersionPipelineRunSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model)
      * [`ModelVersionPipelineRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_computed_fields)
      * [`ModelVersionPipelineRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_config)
      * [`ModelVersionPipelineRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_fields)
      * [`ModelVersionPipelineRunSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_id)
      * [`ModelVersionPipelineRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_version)
      * [`ModelVersionPipelineRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.model_version_id)
      * [`ModelVersionPipelineRunSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.pipeline_run)
      * [`ModelVersionPipelineRunSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.pipeline_run_id)
      * [`ModelVersionPipelineRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.to_model)
      * [`ModelVersionPipelineRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.updated)
      * [`ModelVersionPipelineRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.user)
      * [`ModelVersionPipelineRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.user_id)
      * [`ModelVersionPipelineRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.workspace)
      * [`ModelVersionPipelineRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema.workspace_id)
    * [`ModelVersionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema)
      * [`ModelVersionSchema.artifact_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.artifact_links)
      * [`ModelVersionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.created)
      * [`ModelVersionSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.description)
      * [`ModelVersionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.from_request)
      * [`ModelVersionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.id)
      * [`ModelVersionSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.model)
      * [`ModelVersionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.model_computed_fields)
      * [`ModelVersionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.model_config)
      * [`ModelVersionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.model_fields)
      * [`ModelVersionSchema.model_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.model_id)
      * [`ModelVersionSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.name)
      * [`ModelVersionSchema.number`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.number)
      * [`ModelVersionSchema.pipeline_run_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.pipeline_run_links)
      * [`ModelVersionSchema.pipeline_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.pipeline_runs)
      * [`ModelVersionSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.run_metadata)
      * [`ModelVersionSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.services)
      * [`ModelVersionSchema.stage`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.stage)
      * [`ModelVersionSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.step_runs)
      * [`ModelVersionSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.tags)
      * [`ModelVersionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.to_model)
      * [`ModelVersionSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.update)
      * [`ModelVersionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.updated)
      * [`ModelVersionSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.user)
      * [`ModelVersionSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.user_id)
      * [`ModelVersionSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.workspace)
      * [`ModelVersionSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ModelVersionSchema.workspace_id)
    * [`NamedSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema)
      * [`NamedSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.created)
      * [`NamedSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.id)
      * [`NamedSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.model_computed_fields)
      * [`NamedSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.model_config)
      * [`NamedSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.model_fields)
      * [`NamedSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.name)
      * [`NamedSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.NamedSchema.updated)
    * [`OAuthDeviceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema)
      * [`OAuthDeviceSchema.city`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.city)
      * [`OAuthDeviceSchema.client_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.client_id)
      * [`OAuthDeviceSchema.country`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.country)
      * [`OAuthDeviceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.created)
      * [`OAuthDeviceSchema.device_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.device_code)
      * [`OAuthDeviceSchema.expires`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.expires)
      * [`OAuthDeviceSchema.failed_auth_attempts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.failed_auth_attempts)
      * [`OAuthDeviceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.from_request)
      * [`OAuthDeviceSchema.hostname`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.hostname)
      * [`OAuthDeviceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.id)
      * [`OAuthDeviceSchema.internal_update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.internal_update)
      * [`OAuthDeviceSchema.ip_address`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.ip_address)
      * [`OAuthDeviceSchema.last_login`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.last_login)
      * [`OAuthDeviceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.model_computed_fields)
      * [`OAuthDeviceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.model_config)
      * [`OAuthDeviceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.model_fields)
      * [`OAuthDeviceSchema.os`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.os)
      * [`OAuthDeviceSchema.python_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.python_version)
      * [`OAuthDeviceSchema.region`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.region)
      * [`OAuthDeviceSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.status)
      * [`OAuthDeviceSchema.to_internal_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.to_internal_model)
      * [`OAuthDeviceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.to_model)
      * [`OAuthDeviceSchema.trusted_device`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.trusted_device)
      * [`OAuthDeviceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.update)
      * [`OAuthDeviceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.updated)
      * [`OAuthDeviceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.user)
      * [`OAuthDeviceSchema.user_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.user_code)
      * [`OAuthDeviceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.user_id)
      * [`OAuthDeviceSchema.zenml_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.OAuthDeviceSchema.zenml_version)
    * [`PipelineBuildSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema)
      * [`PipelineBuildSchema.checksum`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.checksum)
      * [`PipelineBuildSchema.contains_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.contains_code)
      * [`PipelineBuildSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.created)
      * [`PipelineBuildSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.from_request)
      * [`PipelineBuildSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.id)
      * [`PipelineBuildSchema.images`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.images)
      * [`PipelineBuildSchema.is_local`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.is_local)
      * [`PipelineBuildSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.model_computed_fields)
      * [`PipelineBuildSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.model_config)
      * [`PipelineBuildSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.model_fields)
      * [`PipelineBuildSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.pipeline)
      * [`PipelineBuildSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.pipeline_id)
      * [`PipelineBuildSchema.python_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.python_version)
      * [`PipelineBuildSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.stack)
      * [`PipelineBuildSchema.stack_checksum`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.stack_checksum)
      * [`PipelineBuildSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.stack_id)
      * [`PipelineBuildSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.to_model)
      * [`PipelineBuildSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.updated)
      * [`PipelineBuildSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.user)
      * [`PipelineBuildSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.user_id)
      * [`PipelineBuildSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.workspace)
      * [`PipelineBuildSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.workspace_id)
      * [`PipelineBuildSchema.zenml_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineBuildSchema.zenml_version)
    * [`PipelineDeploymentSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema)
      * [`PipelineDeploymentSchema.build`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.build)
      * [`PipelineDeploymentSchema.build_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.build_id)
      * [`PipelineDeploymentSchema.client_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.client_environment)
      * [`PipelineDeploymentSchema.client_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.client_version)
      * [`PipelineDeploymentSchema.code_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.code_path)
      * [`PipelineDeploymentSchema.code_reference`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.code_reference)
      * [`PipelineDeploymentSchema.code_reference_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.code_reference_id)
      * [`PipelineDeploymentSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.created)
      * [`PipelineDeploymentSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.from_request)
      * [`PipelineDeploymentSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.id)
      * [`PipelineDeploymentSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.model_computed_fields)
      * [`PipelineDeploymentSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.model_config)
      * [`PipelineDeploymentSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.model_fields)
      * [`PipelineDeploymentSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline)
      * [`PipelineDeploymentSchema.pipeline_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline_configuration)
      * [`PipelineDeploymentSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline_id)
      * [`PipelineDeploymentSchema.pipeline_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline_runs)
      * [`PipelineDeploymentSchema.pipeline_spec`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline_spec)
      * [`PipelineDeploymentSchema.pipeline_version_hash`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.pipeline_version_hash)
      * [`PipelineDeploymentSchema.run_name_template`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.run_name_template)
      * [`PipelineDeploymentSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.schedule)
      * [`PipelineDeploymentSchema.schedule_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.schedule_id)
      * [`PipelineDeploymentSchema.server_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.server_version)
      * [`PipelineDeploymentSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.stack)
      * [`PipelineDeploymentSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.stack_id)
      * [`PipelineDeploymentSchema.step_configurations`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.step_configurations)
      * [`PipelineDeploymentSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.step_runs)
      * [`PipelineDeploymentSchema.template_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.template_id)
      * [`PipelineDeploymentSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.to_model)
      * [`PipelineDeploymentSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.updated)
      * [`PipelineDeploymentSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.user)
      * [`PipelineDeploymentSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.user_id)
      * [`PipelineDeploymentSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.workspace)
      * [`PipelineDeploymentSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineDeploymentSchema.workspace_id)
    * [`PipelineRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema)
      * [`PipelineRunSchema.build`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.build)
      * [`PipelineRunSchema.build_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.build_id)
      * [`PipelineRunSchema.client_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.client_environment)
      * [`PipelineRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.created)
      * [`PipelineRunSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.deployment)
      * [`PipelineRunSchema.deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.deployment_id)
      * [`PipelineRunSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.end_time)
      * [`PipelineRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.from_request)
      * [`PipelineRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.id)
      * [`PipelineRunSchema.logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.logs)
      * [`PipelineRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_computed_fields)
      * [`PipelineRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_config)
      * [`PipelineRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_fields)
      * [`PipelineRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_version)
      * [`PipelineRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_version_id)
      * [`PipelineRunSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.model_versions_pipeline_runs_links)
      * [`PipelineRunSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.name)
      * [`PipelineRunSchema.orchestrator_environment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.orchestrator_environment)
      * [`PipelineRunSchema.orchestrator_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.orchestrator_run_id)
      * [`PipelineRunSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.pipeline)
      * [`PipelineRunSchema.pipeline_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.pipeline_configuration)
      * [`PipelineRunSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.pipeline_id)
      * [`PipelineRunSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.run_metadata)
      * [`PipelineRunSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.schedule)
      * [`PipelineRunSchema.schedule_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.schedule_id)
      * [`PipelineRunSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.services)
      * [`PipelineRunSchema.stack`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.stack)
      * [`PipelineRunSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.stack_id)
      * [`PipelineRunSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.start_time)
      * [`PipelineRunSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.status)
      * [`PipelineRunSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.step_runs)
      * [`PipelineRunSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.tags)
      * [`PipelineRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.to_model)
      * [`PipelineRunSchema.trigger_execution`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.trigger_execution)
      * [`PipelineRunSchema.trigger_execution_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.trigger_execution_id)
      * [`PipelineRunSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.update)
      * [`PipelineRunSchema.update_placeholder()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.update_placeholder)
      * [`PipelineRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.updated)
      * [`PipelineRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.user)
      * [`PipelineRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.user_id)
      * [`PipelineRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.workspace)
      * [`PipelineRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineRunSchema.workspace_id)
    * [`PipelineSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema)
      * [`PipelineSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.builds)
      * [`PipelineSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.created)
      * [`PipelineSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.deployments)
      * [`PipelineSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.description)
      * [`PipelineSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.from_request)
      * [`PipelineSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.id)
      * [`PipelineSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.model_computed_fields)
      * [`PipelineSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.model_config)
      * [`PipelineSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.model_fields)
      * [`PipelineSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.name)
      * [`PipelineSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.runs)
      * [`PipelineSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.schedules)
      * [`PipelineSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.tags)
      * [`PipelineSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.to_model)
      * [`PipelineSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.update)
      * [`PipelineSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.updated)
      * [`PipelineSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.user)
      * [`PipelineSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.user_id)
      * [`PipelineSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.workspace)
      * [`PipelineSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.PipelineSchema.workspace_id)
    * [`RunMetadataSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema)
      * [`RunMetadataSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.artifact_version)
      * [`RunMetadataSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.created)
      * [`RunMetadataSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.id)
      * [`RunMetadataSchema.key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.key)
      * [`RunMetadataSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.model_computed_fields)
      * [`RunMetadataSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.model_config)
      * [`RunMetadataSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.model_fields)
      * [`RunMetadataSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.model_version)
      * [`RunMetadataSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.pipeline_run)
      * [`RunMetadataSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.resource_id)
      * [`RunMetadataSchema.resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.resource_type)
      * [`RunMetadataSchema.stack_component`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.stack_component)
      * [`RunMetadataSchema.stack_component_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.stack_component_id)
      * [`RunMetadataSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.step_run)
      * [`RunMetadataSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.to_model)
      * [`RunMetadataSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.type)
      * [`RunMetadataSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.updated)
      * [`RunMetadataSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.user)
      * [`RunMetadataSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.user_id)
      * [`RunMetadataSchema.value`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.value)
      * [`RunMetadataSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.workspace)
      * [`RunMetadataSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunMetadataSchema.workspace_id)
    * [`RunTemplateSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema)
      * [`RunTemplateSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.created)
      * [`RunTemplateSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.description)
      * [`RunTemplateSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.from_request)
      * [`RunTemplateSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.id)
      * [`RunTemplateSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.model_computed_fields)
      * [`RunTemplateSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.model_config)
      * [`RunTemplateSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.model_fields)
      * [`RunTemplateSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.name)
      * [`RunTemplateSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.runs)
      * [`RunTemplateSchema.source_deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.source_deployment)
      * [`RunTemplateSchema.source_deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.source_deployment_id)
      * [`RunTemplateSchema.tags`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.tags)
      * [`RunTemplateSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.to_model)
      * [`RunTemplateSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.update)
      * [`RunTemplateSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.updated)
      * [`RunTemplateSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.user)
      * [`RunTemplateSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.user_id)
      * [`RunTemplateSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.workspace)
      * [`RunTemplateSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.RunTemplateSchema.workspace_id)
    * [`ScheduleSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema)
      * [`ScheduleSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.active)
      * [`ScheduleSchema.catchup`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.catchup)
      * [`ScheduleSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.created)
      * [`ScheduleSchema.cron_expression`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.cron_expression)
      * [`ScheduleSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.deployment)
      * [`ScheduleSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.end_time)
      * [`ScheduleSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.from_request)
      * [`ScheduleSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.id)
      * [`ScheduleSchema.interval_second`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.interval_second)
      * [`ScheduleSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.model_computed_fields)
      * [`ScheduleSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.model_config)
      * [`ScheduleSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.model_fields)
      * [`ScheduleSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.name)
      * [`ScheduleSchema.orchestrator`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.orchestrator)
      * [`ScheduleSchema.orchestrator_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.orchestrator_id)
      * [`ScheduleSchema.pipeline`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.pipeline)
      * [`ScheduleSchema.pipeline_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.pipeline_id)
      * [`ScheduleSchema.run_once_start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.run_once_start_time)
      * [`ScheduleSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.start_time)
      * [`ScheduleSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.to_model)
      * [`ScheduleSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.update)
      * [`ScheduleSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.updated)
      * [`ScheduleSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.user)
      * [`ScheduleSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.user_id)
      * [`ScheduleSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.workspace)
      * [`ScheduleSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ScheduleSchema.workspace_id)
    * [`SecretSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema)
      * [`SecretSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.created)
      * [`SecretSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.from_request)
      * [`SecretSchema.get_secret_values()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.get_secret_values)
      * [`SecretSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.id)
      * [`SecretSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.model_computed_fields)
      * [`SecretSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.model_config)
      * [`SecretSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.model_fields)
      * [`SecretSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.name)
      * [`SecretSchema.scope`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.scope)
      * [`SecretSchema.set_secret_values()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.set_secret_values)
      * [`SecretSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.to_model)
      * [`SecretSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.update)
      * [`SecretSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.updated)
      * [`SecretSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.user)
      * [`SecretSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.user_id)
      * [`SecretSchema.values`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.values)
      * [`SecretSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.workspace)
      * [`SecretSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.SecretSchema.workspace_id)
    * [`ServerSettingsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema)
      * [`ServerSettingsSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.active)
      * [`ServerSettingsSchema.display_announcements`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.display_announcements)
      * [`ServerSettingsSchema.display_updates`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.display_updates)
      * [`ServerSettingsSchema.enable_analytics`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.enable_analytics)
      * [`ServerSettingsSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.id)
      * [`ServerSettingsSchema.last_user_activity`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.last_user_activity)
      * [`ServerSettingsSchema.logo_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.logo_url)
      * [`ServerSettingsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.model_computed_fields)
      * [`ServerSettingsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.model_config)
      * [`ServerSettingsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.model_fields)
      * [`ServerSettingsSchema.onboarding_state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.onboarding_state)
      * [`ServerSettingsSchema.server_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.server_name)
      * [`ServerSettingsSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.to_model)
      * [`ServerSettingsSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.update)
      * [`ServerSettingsSchema.update_onboarding_state()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.update_onboarding_state)
      * [`ServerSettingsSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServerSettingsSchema.updated)
    * [`ServiceConnectorSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema)
      * [`ServiceConnectorSchema.auth_method`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.auth_method)
      * [`ServiceConnectorSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.components)
      * [`ServiceConnectorSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.configuration)
      * [`ServiceConnectorSchema.connector_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.connector_type)
      * [`ServiceConnectorSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.created)
      * [`ServiceConnectorSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.description)
      * [`ServiceConnectorSchema.expiration_seconds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.expiration_seconds)
      * [`ServiceConnectorSchema.expires_at`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.expires_at)
      * [`ServiceConnectorSchema.expires_skew_tolerance`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.expires_skew_tolerance)
      * [`ServiceConnectorSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.from_request)
      * [`ServiceConnectorSchema.has_labels()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.has_labels)
      * [`ServiceConnectorSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.id)
      * [`ServiceConnectorSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.labels)
      * [`ServiceConnectorSchema.labels_dict`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.labels_dict)
      * [`ServiceConnectorSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.model_computed_fields)
      * [`ServiceConnectorSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.model_config)
      * [`ServiceConnectorSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.model_fields)
      * [`ServiceConnectorSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.name)
      * [`ServiceConnectorSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.resource_id)
      * [`ServiceConnectorSchema.resource_types`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.resource_types)
      * [`ServiceConnectorSchema.resource_types_list`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.resource_types_list)
      * [`ServiceConnectorSchema.secret_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.secret_id)
      * [`ServiceConnectorSchema.supports_instances`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.supports_instances)
      * [`ServiceConnectorSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.to_model)
      * [`ServiceConnectorSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.update)
      * [`ServiceConnectorSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.updated)
      * [`ServiceConnectorSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.user)
      * [`ServiceConnectorSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.user_id)
      * [`ServiceConnectorSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.workspace)
      * [`ServiceConnectorSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceConnectorSchema.workspace_id)
    * [`ServiceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema)
      * [`ServiceSchema.admin_state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.admin_state)
      * [`ServiceSchema.config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.config)
      * [`ServiceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.created)
      * [`ServiceSchema.endpoint`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.endpoint)
      * [`ServiceSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.flavor)
      * [`ServiceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.from_request)
      * [`ServiceSchema.health_check_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.health_check_url)
      * [`ServiceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.id)
      * [`ServiceSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.labels)
      * [`ServiceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.model_computed_fields)
      * [`ServiceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.model_config)
      * [`ServiceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.model_fields)
      * [`ServiceSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.model_version)
      * [`ServiceSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.model_version_id)
      * [`ServiceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.name)
      * [`ServiceSchema.pipeline_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.pipeline_name)
      * [`ServiceSchema.pipeline_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.pipeline_run)
      * [`ServiceSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.pipeline_run_id)
      * [`ServiceSchema.pipeline_step_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.pipeline_step_name)
      * [`ServiceSchema.prediction_url`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.prediction_url)
      * [`ServiceSchema.service_source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.service_source)
      * [`ServiceSchema.service_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.service_type)
      * [`ServiceSchema.state`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.state)
      * [`ServiceSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.status)
      * [`ServiceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.to_model)
      * [`ServiceSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.type)
      * [`ServiceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.update)
      * [`ServiceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.updated)
      * [`ServiceSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.user)
      * [`ServiceSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.user_id)
      * [`ServiceSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.workspace)
      * [`ServiceSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.ServiceSchema.workspace_id)
    * [`StackComponentSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema)
      * [`StackComponentSchema.component_spec_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.component_spec_path)
      * [`StackComponentSchema.configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.configuration)
      * [`StackComponentSchema.connector`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.connector)
      * [`StackComponentSchema.connector_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.connector_id)
      * [`StackComponentSchema.connector_resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.connector_resource_id)
      * [`StackComponentSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.created)
      * [`StackComponentSchema.flavor`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.flavor)
      * [`StackComponentSchema.flavor_schema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.flavor_schema)
      * [`StackComponentSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.id)
      * [`StackComponentSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.labels)
      * [`StackComponentSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.model_computed_fields)
      * [`StackComponentSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.model_config)
      * [`StackComponentSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.model_fields)
      * [`StackComponentSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.name)
      * [`StackComponentSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.run_metadata)
      * [`StackComponentSchema.run_or_step_logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.run_or_step_logs)
      * [`StackComponentSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.schedules)
      * [`StackComponentSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.stacks)
      * [`StackComponentSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.to_model)
      * [`StackComponentSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.type)
      * [`StackComponentSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.update)
      * [`StackComponentSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.updated)
      * [`StackComponentSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.user)
      * [`StackComponentSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.user_id)
      * [`StackComponentSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.workspace)
      * [`StackComponentSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackComponentSchema.workspace_id)
    * [`StackCompositionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema)
      * [`StackCompositionSchema.component_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema.component_id)
      * [`StackCompositionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema.model_computed_fields)
      * [`StackCompositionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema.model_config)
      * [`StackCompositionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema.model_fields)
      * [`StackCompositionSchema.stack_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackCompositionSchema.stack_id)
    * [`StackSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema)
      * [`StackSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.builds)
      * [`StackSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.components)
      * [`StackSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.created)
      * [`StackSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.deployments)
      * [`StackSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.id)
      * [`StackSchema.labels`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.labels)
      * [`StackSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.model_computed_fields)
      * [`StackSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.model_config)
      * [`StackSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.model_fields)
      * [`StackSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.name)
      * [`StackSchema.stack_spec_path`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.stack_spec_path)
      * [`StackSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.to_model)
      * [`StackSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.update)
      * [`StackSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.updated)
      * [`StackSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.user)
      * [`StackSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.user_id)
      * [`StackSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.workspace)
      * [`StackSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StackSchema.workspace_id)
    * [`StepRunInputArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema)
      * [`StepRunInputArtifactSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.artifact_id)
      * [`StepRunInputArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.artifact_version)
      * [`StepRunInputArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.model_computed_fields)
      * [`StepRunInputArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.model_config)
      * [`StepRunInputArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.model_fields)
      * [`StepRunInputArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.name)
      * [`StepRunInputArtifactSchema.step_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.step_id)
      * [`StepRunInputArtifactSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.step_run)
      * [`StepRunInputArtifactSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunInputArtifactSchema.type)
    * [`StepRunOutputArtifactSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema)
      * [`StepRunOutputArtifactSchema.artifact_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.artifact_id)
      * [`StepRunOutputArtifactSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.artifact_version)
      * [`StepRunOutputArtifactSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.model_computed_fields)
      * [`StepRunOutputArtifactSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.model_config)
      * [`StepRunOutputArtifactSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.model_fields)
      * [`StepRunOutputArtifactSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.name)
      * [`StepRunOutputArtifactSchema.step_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.step_id)
      * [`StepRunOutputArtifactSchema.step_run`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.step_run)
      * [`StepRunOutputArtifactSchema.type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunOutputArtifactSchema.type)
    * [`StepRunParentsSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema)
      * [`StepRunParentsSchema.child_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema.child_id)
      * [`StepRunParentsSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema.model_computed_fields)
      * [`StepRunParentsSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema.model_config)
      * [`StepRunParentsSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema.model_fields)
      * [`StepRunParentsSchema.parent_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunParentsSchema.parent_id)
    * [`StepRunSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema)
      * [`StepRunSchema.cache_key`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.cache_key)
      * [`StepRunSchema.code_hash`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.code_hash)
      * [`StepRunSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.created)
      * [`StepRunSchema.deployment`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.deployment)
      * [`StepRunSchema.deployment_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.deployment_id)
      * [`StepRunSchema.docstring`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.docstring)
      * [`StepRunSchema.end_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.end_time)
      * [`StepRunSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.from_request)
      * [`StepRunSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.id)
      * [`StepRunSchema.input_artifacts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.input_artifacts)
      * [`StepRunSchema.logs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.logs)
      * [`StepRunSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.model_computed_fields)
      * [`StepRunSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.model_config)
      * [`StepRunSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.model_fields)
      * [`StepRunSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.model_version)
      * [`StepRunSchema.model_version_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.model_version_id)
      * [`StepRunSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.name)
      * [`StepRunSchema.original_step_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.original_step_run_id)
      * [`StepRunSchema.output_artifacts`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.output_artifacts)
      * [`StepRunSchema.parents`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.parents)
      * [`StepRunSchema.pipeline_run_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.pipeline_run_id)
      * [`StepRunSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.run_metadata)
      * [`StepRunSchema.source_code`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.source_code)
      * [`StepRunSchema.start_time`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.start_time)
      * [`StepRunSchema.status`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.status)
      * [`StepRunSchema.step_configuration`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.step_configuration)
      * [`StepRunSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.to_model)
      * [`StepRunSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.update)
      * [`StepRunSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.updated)
      * [`StepRunSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.user)
      * [`StepRunSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.user_id)
      * [`StepRunSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.workspace)
      * [`StepRunSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.StepRunSchema.workspace_id)
    * [`TagResourceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema)
      * [`TagResourceSchema.artifact`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.artifact)
      * [`TagResourceSchema.artifact_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.artifact_version)
      * [`TagResourceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.created)
      * [`TagResourceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.from_request)
      * [`TagResourceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.id)
      * [`TagResourceSchema.model`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.model)
      * [`TagResourceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.model_computed_fields)
      * [`TagResourceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.model_config)
      * [`TagResourceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.model_fields)
      * [`TagResourceSchema.model_version`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.model_version)
      * [`TagResourceSchema.resource_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.resource_id)
      * [`TagResourceSchema.resource_type`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.resource_type)
      * [`TagResourceSchema.tag`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.tag)
      * [`TagResourceSchema.tag_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.tag_id)
      * [`TagResourceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.to_model)
      * [`TagResourceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagResourceSchema.updated)
    * [`TagSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema)
      * [`TagSchema.color`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.color)
      * [`TagSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.created)
      * [`TagSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.from_request)
      * [`TagSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.id)
      * [`TagSchema.links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.links)
      * [`TagSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.model_computed_fields)
      * [`TagSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.model_config)
      * [`TagSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.model_fields)
      * [`TagSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.name)
      * [`TagSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.to_model)
      * [`TagSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.update)
      * [`TagSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TagSchema.updated)
    * [`TriggerExecutionSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema)
      * [`TriggerExecutionSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.created)
      * [`TriggerExecutionSchema.event_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.event_metadata)
      * [`TriggerExecutionSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.from_request)
      * [`TriggerExecutionSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.id)
      * [`TriggerExecutionSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.model_computed_fields)
      * [`TriggerExecutionSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.model_config)
      * [`TriggerExecutionSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.model_fields)
      * [`TriggerExecutionSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.to_model)
      * [`TriggerExecutionSchema.trigger`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.trigger)
      * [`TriggerExecutionSchema.trigger_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.trigger_id)
      * [`TriggerExecutionSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerExecutionSchema.updated)
    * [`TriggerSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema)
      * [`TriggerSchema.action`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.action)
      * [`TriggerSchema.action_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.action_id)
      * [`TriggerSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.created)
      * [`TriggerSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.description)
      * [`TriggerSchema.event_filter`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.event_filter)
      * [`TriggerSchema.event_source`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.event_source)
      * [`TriggerSchema.event_source_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.event_source_id)
      * [`TriggerSchema.executions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.executions)
      * [`TriggerSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.from_request)
      * [`TriggerSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.id)
      * [`TriggerSchema.is_active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.is_active)
      * [`TriggerSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.model_computed_fields)
      * [`TriggerSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.model_config)
      * [`TriggerSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.model_fields)
      * [`TriggerSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.name)
      * [`TriggerSchema.schedule`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.schedule)
      * [`TriggerSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.to_model)
      * [`TriggerSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.update)
      * [`TriggerSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.updated)
      * [`TriggerSchema.user`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.user)
      * [`TriggerSchema.user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.user_id)
      * [`TriggerSchema.workspace`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.workspace)
      * [`TriggerSchema.workspace_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.TriggerSchema.workspace_id)
    * [`UserSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema)
      * [`UserSchema.actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.actions)
      * [`UserSchema.activation_token`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.activation_token)
      * [`UserSchema.active`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.active)
      * [`UserSchema.api_keys`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.api_keys)
      * [`UserSchema.artifact_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.artifact_versions)
      * [`UserSchema.auth_actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.auth_actions)
      * [`UserSchema.auth_devices`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.auth_devices)
      * [`UserSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.builds)
      * [`UserSchema.code_repositories`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.code_repositories)
      * [`UserSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.components)
      * [`UserSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.created)
      * [`UserSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.deployments)
      * [`UserSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.description)
      * [`UserSchema.email`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.email)
      * [`UserSchema.email_opted_in`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.email_opted_in)
      * [`UserSchema.event_sources`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.event_sources)
      * [`UserSchema.external_user_id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.external_user_id)
      * [`UserSchema.flavors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.flavors)
      * [`UserSchema.from_service_account_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.from_service_account_request)
      * [`UserSchema.from_user_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.from_user_request)
      * [`UserSchema.full_name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.full_name)
      * [`UserSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.id)
      * [`UserSchema.is_admin`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.is_admin)
      * [`UserSchema.is_service_account`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.is_service_account)
      * [`UserSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_computed_fields)
      * [`UserSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_config)
      * [`UserSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_fields)
      * [`UserSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_versions)
      * [`UserSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_versions_artifacts_links)
      * [`UserSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.model_versions_pipeline_runs_links)
      * [`UserSchema.models`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.models)
      * [`UserSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.name)
      * [`UserSchema.password`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.password)
      * [`UserSchema.pipelines`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.pipelines)
      * [`UserSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.run_metadata)
      * [`UserSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.runs)
      * [`UserSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.schedules)
      * [`UserSchema.secrets`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.secrets)
      * [`UserSchema.service_connectors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.service_connectors)
      * [`UserSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.services)
      * [`UserSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.stacks)
      * [`UserSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.step_runs)
      * [`UserSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.to_model)
      * [`UserSchema.to_service_account_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.to_service_account_model)
      * [`UserSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.triggers)
      * [`UserSchema.update_service_account()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.update_service_account)
      * [`UserSchema.update_user()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.update_user)
      * [`UserSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.updated)
      * [`UserSchema.user_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.UserSchema.user_metadata)
    * [`WorkspaceSchema`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema)
      * [`WorkspaceSchema.actions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.actions)
      * [`WorkspaceSchema.artifact_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.artifact_versions)
      * [`WorkspaceSchema.builds`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.builds)
      * [`WorkspaceSchema.code_repositories`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.code_repositories)
      * [`WorkspaceSchema.components`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.components)
      * [`WorkspaceSchema.created`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.created)
      * [`WorkspaceSchema.deployments`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.deployments)
      * [`WorkspaceSchema.description`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.description)
      * [`WorkspaceSchema.event_sources`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.event_sources)
      * [`WorkspaceSchema.flavors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.flavors)
      * [`WorkspaceSchema.from_request()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.from_request)
      * [`WorkspaceSchema.id`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.id)
      * [`WorkspaceSchema.model_computed_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_computed_fields)
      * [`WorkspaceSchema.model_config`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_config)
      * [`WorkspaceSchema.model_fields`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_fields)
      * [`WorkspaceSchema.model_versions`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_versions)
      * [`WorkspaceSchema.model_versions_artifacts_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_versions_artifacts_links)
      * [`WorkspaceSchema.model_versions_pipeline_runs_links`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.model_versions_pipeline_runs_links)
      * [`WorkspaceSchema.models`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.models)
      * [`WorkspaceSchema.name`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.name)
      * [`WorkspaceSchema.pipelines`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.pipelines)
      * [`WorkspaceSchema.run_metadata`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.run_metadata)
      * [`WorkspaceSchema.runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.runs)
      * [`WorkspaceSchema.schedules`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.schedules)
      * [`WorkspaceSchema.secrets`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.secrets)
      * [`WorkspaceSchema.service_connectors`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.service_connectors)
      * [`WorkspaceSchema.services`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.services)
      * [`WorkspaceSchema.stacks`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.stacks)
      * [`WorkspaceSchema.step_runs`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.step_runs)
      * [`WorkspaceSchema.to_model()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.to_model)
      * [`WorkspaceSchema.triggers`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.triggers)
      * [`WorkspaceSchema.update()`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.update)
      * [`WorkspaceSchema.updated`](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.WorkspaceSchema.updated)
* [zenml.zen_stores.secrets_stores package](zenml.zen_stores.secrets_stores.md)
  * [Submodules](zenml.zen_stores.secrets_stores.md#submodules)
  * [zenml.zen_stores.secrets_stores.aws_secrets_store module](zenml.zen_stores.secrets_stores.md#zenml-zen-stores-secrets-stores-aws-secrets-store-module)
  * [zenml.zen_stores.secrets_stores.azure_secrets_store module](zenml.zen_stores.secrets_stores.md#zenml-zen-stores-secrets-stores-azure-secrets-store-module)
  * [zenml.zen_stores.secrets_stores.base_secrets_store module](zenml.zen_stores.secrets_stores.md#module-zenml.zen_stores.secrets_stores.base_secrets_store)
    * [`BaseSecretsStore`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore)
      * [`BaseSecretsStore.CONFIG_TYPE`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.CONFIG_TYPE)
      * [`BaseSecretsStore.TYPE`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.TYPE)
      * [`BaseSecretsStore.config`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.config)
      * [`BaseSecretsStore.convert_config()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.convert_config)
      * [`BaseSecretsStore.create_store()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.create_store)
      * [`BaseSecretsStore.get_store_class()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.get_store_class)
      * [`BaseSecretsStore.model_computed_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.model_computed_fields)
      * [`BaseSecretsStore.model_config`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.model_config)
      * [`BaseSecretsStore.model_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.model_fields)
      * [`BaseSecretsStore.model_post_init()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.model_post_init)
      * [`BaseSecretsStore.type`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.type)
      * [`BaseSecretsStore.zen_store`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore.zen_store)
  * [zenml.zen_stores.secrets_stores.gcp_secrets_store module](zenml.zen_stores.secrets_stores.md#zenml-zen-stores-secrets-stores-gcp-secrets-store-module)
  * [zenml.zen_stores.secrets_stores.hashicorp_secrets_store module](zenml.zen_stores.secrets_stores.md#zenml-zen-stores-secrets-stores-hashicorp-secrets-store-module)
  * [zenml.zen_stores.secrets_stores.secrets_store_interface module](zenml.zen_stores.secrets_stores.md#module-zenml.zen_stores.secrets_stores.secrets_store_interface)
    * [`SecretsStoreInterface`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface)
      * [`SecretsStoreInterface.delete_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface.delete_secret_values)
      * [`SecretsStoreInterface.get_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface.get_secret_values)
      * [`SecretsStoreInterface.store_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface.store_secret_values)
      * [`SecretsStoreInterface.update_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface.update_secret_values)
  * [zenml.zen_stores.secrets_stores.service_connector_secrets_store module](zenml.zen_stores.secrets_stores.md#zenml-zen-stores-secrets-stores-service-connector-secrets-store-module)
  * [zenml.zen_stores.secrets_stores.sql_secrets_store module](zenml.zen_stores.secrets_stores.md#module-zenml.zen_stores.secrets_stores.sql_secrets_store)
    * [`SqlSecretsStore`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore)
      * [`SqlSecretsStore.CONFIG_TYPE`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.CONFIG_TYPE)
      * [`SqlSecretsStore.TYPE`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.TYPE)
      * [`SqlSecretsStore.config`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.config)
      * [`SqlSecretsStore.delete_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.delete_secret_values)
      * [`SqlSecretsStore.engine`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.engine)
      * [`SqlSecretsStore.get_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.get_secret_values)
      * [`SqlSecretsStore.model_computed_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.model_computed_fields)
      * [`SqlSecretsStore.model_config`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.model_config)
      * [`SqlSecretsStore.model_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.model_fields)
      * [`SqlSecretsStore.model_post_init()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.model_post_init)
      * [`SqlSecretsStore.store_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.store_secret_values)
      * [`SqlSecretsStore.update_secret_values()`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.update_secret_values)
      * [`SqlSecretsStore.zen_store`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore.zen_store)
    * [`SqlSecretsStoreConfiguration`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration)
      * [`SqlSecretsStoreConfiguration.encryption_key`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration.encryption_key)
      * [`SqlSecretsStoreConfiguration.model_computed_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration.model_computed_fields)
      * [`SqlSecretsStoreConfiguration.model_config`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration.model_config)
      * [`SqlSecretsStoreConfiguration.model_fields`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration.model_fields)
      * [`SqlSecretsStoreConfiguration.type`](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration.type)
  * [Module contents](zenml.zen_stores.secrets_stores.md#module-zenml.zen_stores.secrets_stores)

## Submodules

## zenml.zen_stores.base_zen_store module

Base Zen Store implementation.

### *class* zenml.zen_stores.base_zen_store.BaseZenStore(skip_default_registrations: bool = False, \*, config: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration))

Bases: `BaseModel`, [`ZenStoreInterface`](#zenml.zen_stores.zen_store_interface.ZenStoreInterface), `ABC`

Base class for accessing and persisting ZenML core objects.

Attributes:
: config: The configuration of the store.

#### CONFIG_TYPE *: ClassVar[Type[[StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration)]]*

#### TYPE *: ClassVar[[StoreType](zenml.md#zenml.enums.StoreType)]*

#### config *: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration)*

#### *classmethod* convert_config(data: Any, validation_info: ValidationInfo) → Any

Wrapper method to handle the raw data.

Args:
: cls: the class handler
  data: the raw input data
  validation_info: the context of the validation.

Returns:
: the validated data

#### *static* create_store(config: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration), skip_default_registrations: bool = False, \*\*kwargs: Any) → [BaseZenStore](#zenml.zen_stores.base_zen_store.BaseZenStore)

Create and initialize a store from a store configuration.

Args:
: config: The store configuration to use.
  skip_default_registrations: If True, the creation of the default
  <br/>
  > stack and user in the store will be skipped.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the store class

Returns:
: The initialized store.

#### *static* get_default_store_config(path: str) → [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration)

Get the default store configuration.

The default store is a SQLite store that saves the DB contents on the
local filesystem.

Args:
: path: The local path where the store DB will be stored.

Returns:
: The default store configuration.

#### get_external_user(user_id: UUID) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Get a user by external ID.

Args:
: user_id: The external ID of the user.

Returns:
: The user with the supplied external ID.

Raises:
: KeyError: If the user doesn’t exist.

#### *static* get_store_class(store_type: [StoreType](zenml.md#zenml.enums.StoreType)) → Type[[BaseZenStore](#zenml.zen_stores.base_zen_store.BaseZenStore)]

Returns the class of the given store type.

Args:
: store_type: The type of the store to get the class for.

Returns:
: The class of the given store type or None if the type is unknown.

Raises:
: TypeError: If the store type is unsupported.

#### *static* get_store_config_class(store_type: [StoreType](zenml.md#zenml.enums.StoreType)) → Type[[StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration)]

Returns the store config class of the given store type.

Args:
: store_type: The type of the store to get the class for.

Returns:
: The config class of the given store type.

#### get_store_info() → [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)

Get information about the store.

Returns:
: Information about the store.

#### *static* get_store_type(url: str) → [StoreType](zenml.md#zenml.enums.StoreType)

Returns the store type associated with a URL schema.

Args:
: url: The store URL.

Returns:
: The store type associated with the supplied URL schema.

Raises:
: TypeError: If no store type was found to support the supplied URL.

#### is_local_store() → bool

Check if the store is local or connected to a local ZenML server.

Returns:
: True if the store is local, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=StoreConfiguration, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* type *: [StoreType](zenml.md#zenml.enums.StoreType)*

The type of the store.

Returns:
: The type of the store.

#### *property* url *: str*

The URL of the store.

Returns:
: The URL of the store.

#### validate_active_config(active_workspace_name_or_id: str | UUID | None = None, active_stack_id: UUID | None = None, config_name: str = '') → Tuple[[WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse), [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)]

Validate the active configuration.

Call this method to validate the supplied active workspace and active
stack values.

This method is guaranteed to return valid workspace ID and stack ID
values. If the supplied workspace and stack are not set or are not valid
(e.g. they do not exist or are not accessible), the default workspace and
default workspace stack will be returned in their stead.

Args:
: active_workspace_name_or_id: The name or ID of the active workspace.
  active_stack_id: The ID of the active stack.
  config_name: The name of the configuration to validate (used in the
  <br/>
  > displayed logs/messages).

Returns:
: A tuple containing the active workspace and active stack.

## zenml.zen_stores.rest_zen_store module

REST Zen Store implementation.

### *class* zenml.zen_stores.rest_zen_store.RestZenStore(skip_default_registrations: bool = False, \*, config: [RestZenStoreConfiguration](#zenml.zen_stores.rest_zen_store.RestZenStoreConfiguration))

Bases: [`BaseZenStore`](#zenml.zen_stores.base_zen_store.BaseZenStore)

Store implementation for accessing data from a REST API.

#### CONFIG_TYPE

alias of [`RestZenStoreConfiguration`](#zenml.zen_stores.rest_zen_store.RestZenStoreConfiguration)

#### TYPE *: ClassVar[[StoreType](zenml.md#zenml.enums.StoreType)]* *= 'rest'*

#### backup_secrets(ignore_errors: bool = True, delete_secrets: bool = False) → None

Backs up all secrets to the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the backup
  : process and attempt to backup all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully backed up from the primary secrets store. Setting
    this flag effectively moves all secrets from the primary secrets
    store to the backup secrets store.

#### clear_session() → None

Clear the authentication session and any cached API tokens.

Raises:
: AuthorizationException: If the API token can’t be reset because
  : the store configuration does not contain username and password
    or an API key to fetch a new token.

#### config *: [RestZenStoreConfiguration](#zenml.zen_stores.rest_zen_store.RestZenStoreConfiguration)*

#### create_action(action: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Create an action.

Args:
: action: The action to create.

Returns:
: The created action.

#### create_api_key(service_account_id: UUID, api_key: [APIKeyRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Create a new API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : create the API key.
  <br/>
  api_key: The API key to create.

Returns:
: The created API key.

#### create_artifact(artifact: [ArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactRequest)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Creates a new artifact.

Args:
: artifact: The artifact to create.

Returns:
: The newly created artifact.

#### create_artifact_version(artifact_version: [ArtifactVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionRequest)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Creates an artifact version.

Args:
: artifact_version: The artifact version to create.

Returns:
: The created artifact version.

#### create_build(build: [PipelineBuildRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildRequest)) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Creates a new build in a workspace.

Args:
: build: The build to create.

Returns:
: The newly created build.

#### create_code_repository(code_repository: [CodeRepositoryRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryRequest)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Creates a new code repository.

Args:
: code_repository: Code repository to be created.

Returns:
: The newly created code repository.

#### create_deployment(deployment: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest)) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Creates a new deployment in a workspace.

Args:
: deployment: The deployment to create.

Returns:
: The newly created deployment.

#### create_event_source(event_source: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Create an event_source.

Args:
: event_source: The event_source to create.

Returns:
: The created event_source.

#### create_flavor(flavor: [FlavorRequest](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorRequest)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Creates a new stack component flavor.

Args:
: flavor: The stack component flavor to create.

Returns:
: The newly created flavor.

#### create_model(model: [ModelRequest](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelRequest)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Creates a new model.

Args:
: model: the Model to be created.

Returns:
: The newly created model.

#### create_model_version(model_version: [ModelVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionRequest)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Creates a new model version.

Args:
: model_version: the Model Version to be created.

Returns:
: The newly created model version.

#### create_model_version_artifact_link(model_version_artifact_link: [ModelVersionArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest)) → [ModelVersionArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse)

Creates a new model version link.

Args:
: model_version_artifact_link: the Model Version to Artifact Link
  : to be created.

Returns:
: The newly created model version to artifact link.

#### create_model_version_pipeline_run_link(model_version_pipeline_run_link: [ModelVersionPipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest)) → [ModelVersionPipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse)

Creates a new model version to pipeline run link.

Args:
: model_version_pipeline_run_link: the Model Version to Pipeline Run
  : Link to be created.

Returns:
: - If Model Version to Pipeline Run Link already exists - returns
    : the existing link.
  - Otherwise, returns the newly created model version to pipeline
    : run link.

#### create_pipeline(pipeline: [PipelineRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineRequest)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Creates a new pipeline in a workspace.

Args:
: pipeline: The pipeline to create.

Returns:
: The newly created pipeline.

#### create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Creates a pipeline run.

Args:
: pipeline_run: The pipeline run to create.

Returns:
: The created pipeline run.

#### create_run_metadata(run_metadata: [RunMetadataRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataRequest)) → List[[RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)]

Creates run metadata.

Args:
: run_metadata: The run metadata to create.

Returns:
: The created run metadata.

#### create_run_step(step_run: [StepRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunRequest)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Creates a step run.

Args:
: step_run: The step run to create.

Returns:
: The created step run.

#### create_run_template(template: [RunTemplateRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateRequest)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Create a new run template.

Args:
: template: The template to create.

Returns:
: The newly created template.

#### create_schedule(schedule: [ScheduleRequest](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleRequest)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Creates a new schedule.

Args:
: schedule: The schedule to create.

Returns:
: The newly created schedule.

#### create_secret(secret: [SecretRequest](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretRequest)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Creates a new secret.

The new secret is also validated against the scoping rules enforced in
the secrets store:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret: The secret to create.

Returns:
: The newly created secret.

#### create_service(service_request: [ServiceRequest](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceRequest)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Create a new service.

Args:
: service_request: The service to create.

Returns:
: The created service.

#### create_service_account(service_account: [ServiceAccountRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountRequest)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Creates a new service account.

Args:
: service_account: Service account to be created.

Returns:
: The newly created service account.

#### create_service_connector(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Creates a new service connector.

Args:
: service_connector: Service connector to be created.

Returns:
: The newly created service connector.

#### create_stack(stack: [StackRequest](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackRequest)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Register a new stack.

Args:
: stack: The stack to register.

Returns:
: The registered stack.

#### create_stack_component(component: [ComponentRequest](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentRequest)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Create a stack component.

Args:
: component: The stack component to create.

Returns:
: The created stack component.

#### create_tag(tag: [TagRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagRequest)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Creates a new tag.

Args:
: tag: the tag to be created.

Returns:
: The newly created tag.

#### create_trigger(trigger: [TriggerRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerRequest)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Create an trigger.

Args:
: trigger: The trigger to create.

Returns:
: The created trigger.

#### create_user(user: [UserRequest](zenml.models.v2.core.md#zenml.models.v2.core.user.UserRequest)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Creates a new user.

Args:
: user: User to be created.

Returns:
: The newly created user.

#### create_workspace(workspace: [WorkspaceRequest](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceRequest)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Creates a new workspace.

Args:
: workspace: The workspace to create.

Returns:
: The newly created workspace.

#### deactivate_user(user_name_or_id: str | UUID) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Deactivates a user.

Args:
: user_name_or_id: The name or ID of the user to delete.

Returns:
: The deactivated user containing the activation token.

#### delete(path: str, params: Dict[str, Any] | None = None, timeout: int | None = None, \*\*kwargs: Any) → Dict[str, Any] | List[Any] | str | int | float | bool | None

Make a DELETE request to the given endpoint path.

Args:
: path: The path to the endpoint.
  params: The query parameters to pass to the endpoint.
  timeout: The request timeout in seconds.
  kwargs: Additional keyword arguments to pass to the request.

Returns:
: The response body.

#### delete_action(action_id: UUID) → None

Delete an action.

Args:
: action_id: The ID of the action to delete.

#### delete_all_model_version_artifact_links(model_version_id: UUID, only_links: bool = True) → None

Deletes all links between model version and an artifact.

Args:
: model_version_id: ID of the model version containing the link.
  only_links: Flag deciding whether to delete only links or all.

#### delete_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID) → None

Delete an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : delete the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to delete.

#### delete_artifact(artifact_id: UUID) → None

Deletes an artifact.

Args:
: artifact_id: The ID of the artifact to delete.

#### delete_artifact_version(artifact_version_id: UUID) → None

Deletes an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to delete.

#### delete_authorized_device(device_id: UUID) → None

Deletes an OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to delete.

#### delete_build(build_id: UUID) → None

Deletes a build.

Args:
: build_id: The ID of the build to delete.

#### delete_code_repository(code_repository_id: UUID) → None

Deletes a code repository.

Args:
: code_repository_id: The ID of the code repository to delete.

#### delete_deployment(deployment_id: UUID) → None

Deletes a deployment.

Args:
: deployment_id: The ID of the deployment to delete.

#### delete_event_source(event_source_id: UUID) → None

Delete an event_source.

Args:
: event_source_id: The ID of the event_source to delete.

#### delete_flavor(flavor_id: UUID) → None

Delete a stack component flavor.

Args:
: flavor_id: The ID of the stack component flavor to delete.

#### delete_model(model_name_or_id: str | UUID) → None

Deletes a model.

Args:
: model_name_or_id: name or id of the model to be deleted.

#### delete_model_version(model_version_id: UUID) → None

Deletes a model version.

Args:
: model_version_id: name or id of the model version to be deleted.

#### delete_model_version_artifact_link(model_version_id: UUID, model_version_artifact_link_name_or_id: str | UUID) → None

Deletes a model version to artifact link.

Args:
: model_version_id: ID of the model version containing the link.
  model_version_artifact_link_name_or_id: name or ID of the model
  <br/>
  > version to artifact link to be deleted.

#### delete_model_version_pipeline_run_link(model_version_id: UUID, model_version_pipeline_run_link_name_or_id: str | UUID) → None

Deletes a model version to pipeline run link.

Args:
: model_version_id: ID of the model version containing the link.
  model_version_pipeline_run_link_name_or_id: name or ID of the model version to pipeline run link to be deleted.

#### delete_pipeline(pipeline_id: UUID) → None

Deletes a pipeline.

Args:
: pipeline_id: The ID of the pipeline to delete.

#### delete_run(run_id: UUID) → None

Deletes a pipeline run.

Args:
: run_id: The ID of the pipeline run to delete.

#### delete_run_template(template_id: UUID) → None

Delete a run template.

Args:
: template_id: The ID of the template to delete.

#### delete_schedule(schedule_id: UUID) → None

Deletes a schedule.

Args:
: schedule_id: The ID of the schedule to delete.

#### delete_secret(secret_id: UUID) → None

Delete a secret.

Args:
: secret_id: The id of the secret to delete.

#### delete_service(service_id: UUID) → None

Delete a service.

Args:
: service_id: The ID of the service to delete.

#### delete_service_account(service_account_name_or_id: str | UUID) → None

Delete a service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to delete.

#### delete_service_connector(service_connector_id: UUID) → None

Deletes a service connector.

Args:
: service_connector_id: The ID of the service connector to delete.

#### delete_stack(stack_id: UUID) → None

Delete a stack.

Args:
: stack_id: The ID of the stack to delete.

#### delete_stack_component(component_id: UUID) → None

Delete a stack component.

Args:
: component_id: The ID of the stack component to delete.

#### delete_tag(tag_name_or_id: str | UUID) → None

Deletes a tag.

Args:
: tag_name_or_id: name or id of the tag to delete.

#### delete_trigger(trigger_id: UUID) → None

Delete an trigger.

Args:
: trigger_id: The ID of the trigger to delete.

#### delete_trigger_execution(trigger_execution_id: UUID) → None

Delete a trigger execution.

Args:
: trigger_execution_id: The ID of the trigger execution to delete.

#### delete_user(user_name_or_id: str | UUID) → None

Deletes a user.

Args:
: user_name_or_id: The name or ID of the user to delete.

#### delete_workspace(workspace_name_or_id: str | UUID) → None

Deletes a workspace.

Args:
: workspace_name_or_id: Name or ID of the workspace to delete.

#### get(path: str, params: Dict[str, Any] | None = None, timeout: int | None = None, \*\*kwargs: Any) → Dict[str, Any] | List[Any] | str | int | float | bool | None

Make a GET request to the given endpoint path.

Args:
: path: The path to the endpoint.
  params: The query parameters to pass to the endpoint.
  timeout: The request timeout in seconds.
  kwargs: Additional keyword arguments to pass to the request.

Returns:
: The response body.

#### get_action(action_id: UUID, hydrate: bool = True) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Get an action by ID.

Args:
: action_id: The ID of the action to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The action.

#### get_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, hydrate: bool = True) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Get an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to fetch
  : the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The API key with the given ID.

#### get_api_token(pipeline_id: UUID | None = None, schedule_id: UUID | None = None, expires_minutes: int | None = None) → str

Get an API token for a workload.

Args:
: pipeline_id: The ID of the pipeline to get a token for.
  schedule_id: The ID of the schedule to get a token for.
  expires_minutes: The number of minutes for which the token should
  <br/>
  > be valid. If not provided, the token will be valid indefinitely.

Returns:
: The API token.

Raises:
: ValueError: if the server response is not valid.

#### get_artifact(artifact_id: UUID, hydrate: bool = True) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Gets an artifact.

Args:
: artifact_id: The ID of the artifact to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact.

#### get_artifact_version(artifact_version_id: UUID, hydrate: bool = True) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Gets an artifact.

Args:
: artifact_version_id: The ID of the artifact version to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact version.

#### get_artifact_visualization(artifact_visualization_id: UUID, hydrate: bool = True) → [ArtifactVisualizationResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Gets an artifact visualization.

Args:
: artifact_visualization_id: The ID of the artifact visualization to
  : get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The artifact visualization.

#### get_authorized_device(device_id: UUID, hydrate: bool = True) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Gets a specific OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested device, if it was found.

#### get_build(build_id: UUID, hydrate: bool = True) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Get a build with a given ID.

Args:
: build_id: ID of the build.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The build.

#### get_code_reference(code_reference_id: UUID, hydrate: bool = True) → [CodeReferenceResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Gets a code reference.

Args:
: code_reference_id: The ID of the code reference to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The code reference.

#### get_code_repository(code_repository_id: UUID, hydrate: bool = True) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Gets a specific code repository.

Args:
: code_repository_id: The ID of the code repository to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested code repository, if it was found.

#### get_deployment(deployment_id: UUID, hydrate: bool = True) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Get a deployment with a given ID.

Args:
: deployment_id: ID of the deployment.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The deployment.

#### get_deployment_id() → UUID

Get the ID of the deployment.

Returns:
: The ID of the deployment.

#### get_event_source(event_source_id: UUID, hydrate: bool = True) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Get an event_source by ID.

Args:
: event_source_id: The ID of the event_source to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The event_source.

#### get_flavor(flavor_id: UUID, hydrate: bool = True) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Get a stack component flavor by ID.

Args:
: flavor_id: The ID of the stack component flavor to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component flavor.

#### get_logs(logs_id: UUID, hydrate: bool = True) → [LogsResponse](zenml.models.v2.core.md#zenml.models.v2.core.logs.LogsResponse)

Gets logs with the given ID.

Args:
: logs_id: The ID of the logs to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The logs.

#### get_model(model_name_or_id: str | UUID, hydrate: bool = True) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Get an existing model.

Args:
: model_name_or_id: name or id of the model to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The model of interest.

#### get_model_version(model_version_id: UUID, hydrate: bool = True) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get an existing model version.

Args:
: model_version_id: name, id, stage or number of the model version to
  : be retrieved. If skipped - latest is retrieved.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The model version of interest.

#### get_or_create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → Tuple[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse), bool]

Gets or creates a pipeline run.

If a run with the same ID or name already exists, it is returned.
Otherwise, a new run is created.

Args:
: pipeline_run: The pipeline run to get or create.

Returns:
: The pipeline run, and a boolean indicating whether the run was
  created or not.

#### get_pipeline(pipeline_id: UUID, hydrate: bool = True) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Get a pipeline with a given ID.

Args:
: pipeline_id: ID of the pipeline.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline.

#### get_run(run_name_or_id: UUID | str, hydrate: bool = True) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Gets a pipeline run.

Args:
: run_name_or_id: The name or ID of the pipeline run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline run.

#### get_run_metadata(run_metadata_id: UUID, hydrate: bool = True) → [RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Gets run metadata with the given ID.

Args:
: run_metadata_id: The ID of the run metadata to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The run metadata.

#### get_run_step(step_run_id: UUID, hydrate: bool = True) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Get a step run by ID.

Args:
: step_run_id: The ID of the step run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The step run.

#### get_run_template(template_id: UUID, hydrate: bool = True) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Get a run template with a given ID.

Args:
: template_id: ID of the template.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The template.

#### get_schedule(schedule_id: UUID, hydrate: bool = True) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Get a schedule with a given ID.

Args:
: schedule_id: ID of the schedule.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The schedule.

#### get_secret(secret_id: UUID, hydrate: bool = True) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Get a secret by ID.

Args:
: secret_id: The ID of the secret to fetch.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The secret.

#### get_server_settings(hydrate: bool = True) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Get the server settings.

Args:
: hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The server settings.

#### get_service(service_id: UUID, hydrate: bool = True) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Get a service.

Args:
: service_id: The ID of the service to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The service.

#### get_service_account(service_account_name_or_id: str | UUID, hydrate: bool = True) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Gets a specific service account.

Args:
: service_account_name_or_id: The name or ID of the service account to
  : get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The requested service account, if it was found.

#### get_service_connector(service_connector_id: UUID, hydrate: bool = True) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Gets a specific service connector.

Args:
: service_connector_id: The ID of the service connector to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested service connector, if it was found.

#### get_service_connector_client(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Get a service connector client for a service connector and given resource.

Args:
: service_connector_id: The ID of the base service connector to use.
  resource_type: The type of resource to get a client for.
  resource_id: The ID of the resource to get a client for.

Returns:
: A service connector client that can be used to access the given
  resource.

#### get_service_connector_type(connector_type: str) → [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)

Returns the requested service connector type.

Args:
: connector_type: the service connector type identifier.

Returns:
: The requested service connector type.

#### get_stack(stack_id: UUID, hydrate: bool = True) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Get a stack by its unique ID.

Args:
: stack_id: The ID of the stack to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack with the given ID.

#### get_stack_component(component_id: UUID, hydrate: bool = True) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Get a stack component by ID.

Args:
: component_id: The ID of the stack component to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component.

#### get_stack_deployment_config(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None) → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the cloud provider console URL and configuration needed to deploy the ZenML stack.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.

Returns:
: The cloud provider console URL and configuration needed to deploy
  the ZenML stack to the specified cloud provider.

#### get_stack_deployment_info(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)) → [StackDeploymentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentInfo)

Get information about a stack deployment provider.

Args:
: provider: The stack deployment provider.

Returns:
: Information about the stack deployment provider.

#### get_stack_deployment_stack(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None, date_start: datetime | None = None) → [DeployedStack](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.DeployedStack) | None

Return a matching ZenML stack that was deployed and registered.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.
  date_start: The date when the deployment started.

Returns:
: The ZenML stack that was deployed and registered or None if the
  stack was not found.

#### get_store_info() → [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)

Get information about the server.

Returns:
: Information about the server.

#### get_tag(tag_name_or_id: str | UUID, hydrate: bool = True) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Get an existing tag.

Args:
: tag_name_or_id: name or id of the tag to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The tag of interest.

#### get_trigger(trigger_id: UUID, hydrate: bool = True) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Get a trigger by ID.

Args:
: trigger_id: The ID of the trigger to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger.

#### get_trigger_execution(trigger_execution_id: UUID, hydrate: bool = True) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Get an trigger execution by ID.

Args:
: trigger_execution_id: The ID of the trigger execution to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger execution.

#### get_user(user_name_or_id: str | UUID | None = None, include_private: bool = False, hydrate: bool = True) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Gets a specific user, when no id is specified get the active user.

The include_private parameter is ignored here as it is handled
implicitly by the /current-user endpoint that is queried when no
user_name_or_id is set. Raises a KeyError in case a user with that id
does not exist.

Args:
: user_name_or_id: The name or ID of the user to get.
  include_private: Whether to include private user information.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested user, if it was found.

#### get_workspace(workspace_name_or_id: UUID | str, hydrate: bool = True) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Get an existing workspace by name or ID.

Args:
: workspace_name_or_id: Name or ID of the workspace to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested workspace.

#### list_actions(action_filter_model: [ActionFilter](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ActionResponse](zenml.models.md#zenml.models.ActionResponse)]

List all actions matching the given filter criteria.

Args:
: action_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all actions matching the filter criteria.

#### list_api_keys(service_account_id: UUID, filter_model: [APIKeyFilter](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[APIKeyResponse](zenml.models.md#zenml.models.APIKeyResponse)]

List all API keys for a service account matching the given filter criteria.

Args:
: service_account_id: The ID of the service account for which to list
  : the API keys.
  <br/>
  filter_model: All filter parameters including pagination
  : params
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all API keys matching the filter criteria.

#### list_artifact_versions(artifact_version_filter_model: [ArtifactVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]

List all artifact versions matching the given filter criteria.

Args:
: artifact_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifact versions matching the filter criteria.

#### list_artifacts(filter_model: [ArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactResponse](zenml.models.md#zenml.models.ArtifactResponse)]

List all artifacts matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifacts matching the filter criteria.

#### list_authorized_devices(filter_model: [OAuthDeviceFilter](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[OAuthDeviceResponse](zenml.models.md#zenml.models.OAuthDeviceResponse)]

List all OAuth 2.0 authorized devices for a user.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all matching OAuth 2.0 authorized devices.

#### list_builds(build_filter_model: [PipelineBuildFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse)]

List all builds matching the given filter criteria.

Args:
: build_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all builds matching the filter criteria.

#### list_code_repositories(filter_model: [CodeRepositoryFilter](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[CodeRepositoryResponse](zenml.models.md#zenml.models.CodeRepositoryResponse)]

List all code repositories.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all code repositories.

#### list_deployments(deployment_filter_model: [PipelineDeploymentFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)]

List all deployments matching the given filter criteria.

Args:
: deployment_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all deployments matching the filter criteria.

#### list_event_sources(event_source_filter_model: [EventSourceFilter](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[EventSourceResponse](zenml.models.md#zenml.models.EventSourceResponse)]

List all event_sources matching the given filter criteria.

Args:
: event_source_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all event_sources matching the filter criteria.

#### list_flavors(flavor_filter_model: [FlavorFilter](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[FlavorResponse](zenml.models.md#zenml.models.FlavorResponse)]

List all stack component flavors matching the given filter criteria.

Args:
: flavor_filter_model: All filter parameters including pagination
  : params
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: List of all the stack component flavors matching the given criteria.

#### list_model_version_artifact_links(model_version_artifact_link_filter_model: [ModelVersionArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionArtifactResponse](zenml.models.md#zenml.models.ModelVersionArtifactResponse)]

Get all model version to artifact links by filter.

Args:
: model_version_artifact_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to artifact links.

#### list_model_version_pipeline_run_links(model_version_pipeline_run_link_filter_model: [ModelVersionPipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionPipelineRunResponse](zenml.models.md#zenml.models.ModelVersionPipelineRunResponse)]

Get all model version to pipeline run links by filter.

Args:
: model_version_pipeline_run_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to pipeline run links.

#### list_model_versions(model_version_filter_model: [ModelVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionFilter), model_name_or_id: str | UUID | None = None, hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionResponse](zenml.models.md#zenml.models.ModelVersionResponse)]

Get all model versions by filter.

Args:
: model_name_or_id: name or id of the model containing the model
  : versions.
  <br/>
  model_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model versions.

#### list_models(model_filter_model: [ModelFilter](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelResponse](zenml.models.md#zenml.models.ModelResponse)]

Get all models by filter.

Args:
: model_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all models.

#### list_pipelines(pipeline_filter_model: [PipelineFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineResponse](zenml.models.md#zenml.models.PipelineResponse)]

List all pipelines matching the given filter criteria.

Args:
: pipeline_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipelines matching the filter criteria.

#### list_run_metadata(run_metadata_filter_model: [RunMetadataFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]

List run metadata.

Args:
: run_metadata_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The run metadata.

#### list_run_steps(step_run_filter_model: [StepRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)]

List all step runs matching the given filter criteria.

Args:
: step_run_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all step runs matching the filter criteria.

#### list_run_templates(template_filter_model: [RunTemplateFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunTemplateResponse](zenml.models.md#zenml.models.RunTemplateResponse)]

List all run templates matching the given filter criteria.

Args:
: template_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all templates matching the filter criteria.

#### list_runs(runs_filter_model: [PipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]

List all pipeline runs matching the given filter criteria.

Args:
: runs_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipeline runs matching the filter criteria.

#### list_schedules(schedule_filter_model: [ScheduleFilter](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse)]

List all schedules in the workspace.

Args:
: schedule_filter_model: All filter parameters including pagination
  : params
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of schedules.

#### list_secrets(secret_filter_model: [SecretFilter](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[SecretResponse](zenml.models.md#zenml.models.SecretResponse)]

List all secrets matching the given filter criteria.

Note that returned secrets do not include any secret values. To fetch
the secret values, use get_secret.

Args:
: secret_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all secrets matching the filter criteria, with pagination
  information and sorted according to the filter criteria. The
  returned secrets do not include any secret values, only metadata. To
  fetch the secret values, use get_secret individually with each
  secret.

#### list_service_accounts(filter_model: [ServiceAccountFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceAccountResponse](zenml.models.md#zenml.models.ServiceAccountResponse)]

List all service accounts.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of filtered service accounts.

#### list_service_connector_resources(workspace_name_or_id: str | UUID, connector_type: str | None = None, resource_type: str | None = None, resource_id: str | None = None) → List[[ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)]

List resources that can be accessed by service connectors.

Args:
: workspace_name_or_id: The name or ID of the workspace to scope to.
  connector_type: The type of service connector to scope to.
  resource_type: The type of resource to scope to.
  resource_id: The ID of the resource to scope to.

Returns:
: The matching list of resources that available service
  connectors have access to.

#### list_service_connector_types(connector_type: str | None = None, resource_type: str | None = None, auth_method: str | None = None) → List[[ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)]

Get a list of service connector types.

Args:
: connector_type: Filter by connector type.
  resource_type: Filter by resource type.
  auth_method: Filter by authentication method.

Returns:
: List of service connector types.

#### list_service_connectors(filter_model: [ServiceConnectorFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse)]

List all service connectors.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all service connectors.

#### list_services(filter_model: [ServiceFilter](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)]

List all services matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all services matching the filter criteria.

#### list_stack_components(component_filter_model: [ComponentFilter](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]

List all stack components matching the given filter criteria.

Args:
: component_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stack components matching the filter criteria.

#### list_stacks(stack_filter_model: [StackFilter](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StackResponse](zenml.models.md#zenml.models.StackResponse)]

List all stacks matching the given filter criteria.

Args:
: stack_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stacks matching the filter criteria.

#### list_tags(tag_filter_model: [TagFilter](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TagResponse](zenml.models.md#zenml.models.TagResponse)]

Get all tags by filter.

Args:
: tag_filter_model: All filter parameters including pagination params.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: A page of all tags.

#### list_trigger_executions(trigger_execution_filter_model: [TriggerExecutionFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)]

List all trigger executions matching the given filter criteria.

Args:
: trigger_execution_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all trigger executions matching the filter criteria.

#### list_triggers(trigger_filter_model: [TriggerFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)]

List all triggers matching the given filter criteria.

Args:
: trigger_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all triggers matching the filter criteria.

#### list_users(user_filter_model: [UserFilter](zenml.models.v2.core.md#zenml.models.v2.core.user.UserFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[UserResponse](zenml.models.md#zenml.models.UserResponse)]

List all users.

Args:
: user_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all users.

#### list_workspaces(workspace_filter_model: [WorkspaceFilter](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)]

List all workspace matching the given filter criteria.

Args:
: workspace_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all workspace matching the filter criteria.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=RestZenStoreConfiguration, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### post(path: str, body: BaseModel, params: Dict[str, Any] | None = None, timeout: int | None = None, \*\*kwargs: Any) → Dict[str, Any] | List[Any] | str | int | float | bool | None

Make a POST request to the given endpoint path.

Args:
: path: The path to the endpoint.
  body: The body to send.
  params: The query parameters to pass to the endpoint.
  timeout: The request timeout in seconds.
  kwargs: Additional keyword arguments to pass to the request.

Returns:
: The response body.

#### prune_artifact_versions(only_versions: bool = True) → None

Prunes unused artifact versions and their artifacts.

Args:
: only_versions: Only delete artifact versions, keeping artifacts

#### put(path: str, body: BaseModel | None = None, params: Dict[str, Any] | None = None, timeout: int | None = None, \*\*kwargs: Any) → Dict[str, Any] | List[Any] | str | int | float | bool | None

Make a PUT request to the given endpoint path.

Args:
: path: The path to the endpoint.
  body: The body to send.
  params: The query parameters to pass to the endpoint.
  timeout: The request timeout in seconds.
  kwargs: Additional keyword arguments to pass to the request.

Returns:
: The response body.

#### restore_secrets(ignore_errors: bool = False, delete_secrets: bool = False) → None

Restore all secrets from the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the
  : restore process and attempt to restore all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully restored from the backup secrets store. Setting
    this flag effectively moves all secrets from the backup secrets
    store to the primary secrets store.

#### rotate_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, rotate_request: [APIKeyRotateRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRotateRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Rotate an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : rotate the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to rotate.
  rotate_request: The rotate request on the API key.

Returns:
: The updated API key.

#### run_template(template_id: UUID, run_configuration: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) | None = None) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Run a template.

Args:
: template_id: The ID of the template to run.
  run_configuration: Configuration for the run.

Raises:
: RuntimeError: If the server does not support running a template.

Returns:
: Model of the pipeline run.

#### *property* session *: Session*

Authenticate to the ZenML server.

Returns:
: A requests session with the authentication token.

#### set_api_key(api_key: str) → None

Set the API key to use for authentication.

Args:
: api_key: The API key to use for authentication.

#### update_action(action_id: UUID, action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Update an existing action.

Args:
: action_id: The ID of the action to update.
  action_update: The update to be applied to the action.

Returns:
: The updated action.

#### update_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, api_key_update: [APIKeyUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyUpdate)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Update an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : update the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to update.
  api_key_update: The update request on the API key.

Returns:
: The updated API key.

#### update_artifact(artifact_id: UUID, artifact_update: [ArtifactUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactUpdate)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Updates an artifact.

Args:
: artifact_id: The ID of the artifact to update.
  artifact_update: The update to be applied to the artifact.

Returns:
: The updated artifact.

#### update_artifact_version(artifact_version_id: UUID, artifact_version_update: [ArtifactVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionUpdate)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Updates an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to update.
  artifact_version_update: The update to be applied to the artifact
  <br/>
  > version.

Returns:
: The updated artifact version.

#### update_authorized_device(device_id: UUID, update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Updates an existing OAuth 2.0 authorized device for internal use.

Args:
: device_id: The ID of the device to update.
  update: The update to be applied to the device.

Returns:
: The updated OAuth 2.0 authorized device.

#### update_code_repository(code_repository_id: UUID, update: [CodeRepositoryUpdate](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryUpdate)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Updates an existing code repository.

Args:
: code_repository_id: The ID of the code repository to update.
  update: The update to be applied to the code repository.

Returns:
: The updated code repository.

#### update_event_source(event_source_id: UUID, event_source_update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Update an existing event_source.

Args:
: event_source_id: The ID of the event_source to update.
  event_source_update: The update to be applied to the event_source.

Returns:
: The updated event_source.

#### update_flavor(flavor_id: UUID, flavor_update: [FlavorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorUpdate)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Updates an existing user.

Args:
: flavor_id: The id of the flavor to update.
  flavor_update: The update to be applied to the flavor.

Returns:
: The updated flavor.

#### update_model(model_id: UUID, model_update: [ModelUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelUpdate)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Updates an existing model.

Args:
: model_id: UUID of the model to be updated.
  model_update: the Model to be updated.

Returns:
: The updated model.

#### update_model_version(model_version_id: UUID, model_version_update_model: [ModelVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionUpdate)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get all model versions by filter.

Args:
: model_version_id: The ID of model version to be updated.
  model_version_update_model: The model version to be updated.

Returns:
: An updated model version.

#### update_pipeline(pipeline_id: UUID, pipeline_update: [PipelineUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineUpdate)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Updates a pipeline.

Args:
: pipeline_id: The ID of the pipeline to be updated.
  pipeline_update: The update to be applied.

Returns:
: The updated pipeline.

#### update_run(run_id: UUID, run_update: [PipelineRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunUpdate)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Updates a pipeline run.

Args:
: run_id: The ID of the pipeline run to update.
  run_update: The update to be applied to the pipeline run.

Returns:
: The updated pipeline run.

#### update_run_step(step_run_id: UUID, step_run_update: [StepRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunUpdate)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Updates a step run.

Args:
: step_run_id: The ID of the step to update.
  step_run_update: The update to be applied to the step.

Returns:
: The updated step run.

#### update_run_template(template_id: UUID, template_update: [RunTemplateUpdate](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateUpdate)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Updates a run template.

Args:
: template_id: The ID of the template to update.
  template_update: The update to apply.

Returns:
: The updated template.

#### update_schedule(schedule_id: UUID, schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Updates a schedule.

Args:
: schedule_id: The ID of the schedule to be updated.
  schedule_update: The update to be applied.

Returns:
: The updated schedule.

#### update_secret(secret_id: UUID, secret_update: [SecretUpdate](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretUpdate)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Updates a secret.

Secret values that are specified as None in the update that are
present in the existing secret are removed from the existing secret.
Values that are present in both secrets are overwritten. All other
values in both the existing secret and the update are kept (merged).

If the update includes a change of name or scope, the scoping rules
enforced in the secrets store are used to validate the update:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret_id: The ID of the secret to be updated.
  secret_update: The update to be applied.

Returns:
: The updated secret.

#### update_server_settings(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate)) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Update the server settings.

Args:
: settings_update: The server settings update.

Returns:
: The updated server settings.

#### update_service(service_id: UUID, update: [ServiceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceUpdate)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Update a service.

Args:
: service_id: The ID of the service to update.
  update: The update to be applied to the service.

Returns:
: The updated service.

#### update_service_account(service_account_name_or_id: str | UUID, service_account_update: [ServiceAccountUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountUpdate)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Updates an existing service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to update.
  <br/>
  service_account_update: The update to be applied to the service
  : account.

Returns:
: The updated service account.

#### update_service_connector(service_connector_id: UUID, update: [ServiceConnectorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorUpdate)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Updates an existing service connector.

The update model contains the fields to be updated. If a field value is
set to None in the model, the field is not updated, but there are
special rules concerning some fields:

* the configuration and secrets fields together represent a full

valid configuration update, not just a partial update. If either is
set (i.e. not None) in the update, their values are merged together and
will replace the existing configuration and secrets values.
\* the resource_id field value is also a full replacement value: if set
to None, the resource ID is removed from the service connector.
\* the expiration_seconds field value is also a full replacement value:
if set to None, the expiration is removed from the service connector.
\* the secret_id field value in the update is ignored, given that
secrets are managed internally by the ZenML store.
\* the labels field is also a full labels update: if set (i.e. not
None), all existing labels are removed and replaced by the new labels
in the update.

Args:
: service_connector_id: The ID of the service connector to update.
  update: The update to be applied to the service connector.

Returns:
: The updated service connector.

#### update_stack(stack_id: UUID, stack_update: [StackUpdate](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackUpdate)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Update a stack.

Args:
: stack_id: The ID of the stack update.
  stack_update: The update request on the stack.

Returns:
: The updated stack.

#### update_stack_component(component_id: UUID, component_update: [ComponentUpdate](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentUpdate)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Update an existing stack component.

Args:
: component_id: The ID of the stack component to update.
  component_update: The update to be applied to the stack component.

Returns:
: The updated stack component.

#### update_tag(tag_name_or_id: str | UUID, tag_update_model: [TagUpdate](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagUpdate)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Update tag.

Args:
: tag_name_or_id: name or id of the tag to be updated.
  tag_update_model: Tag to use for the update.

Returns:
: An updated tag.

#### update_trigger(trigger_id: UUID, trigger_update: [TriggerUpdate](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerUpdate)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Update an existing trigger.

Args:
: trigger_id: The ID of the trigger to update.
  trigger_update: The update to be applied to the trigger.

Returns:
: The updated trigger.

#### update_user(user_id: UUID, user_update: [UserUpdate](zenml.models.v2.core.md#zenml.models.v2.core.user.UserUpdate)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Updates an existing user.

Args:
: user_id: The id of the user to update.
  user_update: The update to be applied to the user.

Returns:
: The updated user.

#### update_workspace(workspace_id: UUID, workspace_update: [WorkspaceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceUpdate)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Update an existing workspace.

Args:
: workspace_id: The ID of the workspace to be updated.
  workspace_update: The update to be applied to the workspace.

Returns:
: The updated workspace.

#### verify_service_connector(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None, list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector instance has access to one or more resources.

Args:
: service_connector_id: The ID of the service connector to verify.
  resource_type: The type of resource to verify access to.
  resource_id: The ID of the resource to verify access to.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector and matching the supplied resource
  > type and ID are returned.

Returns:
: The list of resources that the service connector has access to,
  scoped to the supplied resource type and ID, if provided.

#### verify_service_connector_config(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest), list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector configuration has access to resources.

Args:
: service_connector: The service connector configuration to verify.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector and matching the supplied resource
  > type and ID are returned.

Returns:
: The list of resources that the service connector configuration has
  access to.

### *class* zenml.zen_stores.rest_zen_store.RestZenStoreConfiguration(\*, type: [StoreType](zenml.md#zenml.enums.StoreType) = StoreType.REST, url: str, secrets_store: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, backup_secrets_store: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, username: str | None = None, password: str | None = None, api_key: str | None = None, api_token: str | None = None, verify_ssl: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = True, http_timeout: int = 30)

Bases: [`StoreConfiguration`](zenml.config.md#zenml.config.store_config.StoreConfiguration)

REST ZenML store configuration.

Attributes:
: type: The type of the store.
  username: The username to use to connect to the Zen server.
  password: The password to use to connect to the Zen server.
  api_key: The service account API key to use to connect to the Zen
  <br/>
  > server.
  <br/>
  api_token: The API token to use to connect to the Zen server. Generated
  : by the client and stored in the configuration file on the first
    login and every time the API key is refreshed.
  <br/>
  verify_ssl: Either a boolean, in which case it controls whether we
  : verify the server’s TLS certificate, or a string, in which case it
    must be a path to a CA bundle to use or the CA bundle value itself.
  <br/>
  http_timeout: The timeout to use for all requests.

#### api_key *: str | None*

#### api_token *: str | None*

#### expand_certificates() → None

Expands the certificates in the verify_ssl field.

#### http_timeout *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'api_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'api_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'backup_secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'http_timeout': FieldInfo(annotation=int, required=False, default=30), 'password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'type': FieldInfo(annotation=StoreType, required=False, default=<StoreType.REST: 'rest'>), 'url': FieldInfo(annotation=str, required=True), 'username': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'verify_ssl': FieldInfo(annotation=Union[bool, str], required=False, default=True, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: str | None*

#### *classmethod* supports_url_scheme(url: str) → bool

Check if a URL scheme is supported by this store.

Args:
: url: The URL to check.

Returns:
: True if the URL scheme is supported, False otherwise.

#### type *: [StoreType](zenml.md#zenml.enums.StoreType)*

#### username *: str | None*

#### validate_credentials() → [RestZenStoreConfiguration](#zenml.zen_stores.rest_zen_store.RestZenStoreConfiguration)

Validates the credentials provided in the values dictionary.

Raises:
: ValueError: If neither api_token nor username nor api_key is set.

Returns:
: The values dictionary.

#### *classmethod* validate_url(url: str) → str

Validates that the URL is a well-formed REST store URL.

Args:
: url: The URL to be validated.

Returns:
: The validated URL without trailing slashes.

Raises:
: ValueError: If the URL is not a well-formed REST store URL.

#### *classmethod* validate_verify_ssl(verify_ssl: bool | str) → bool | str

Validates that the verify_ssl either points to a file or is a bool.

Args:
: verify_ssl: The verify_ssl value to be validated.

Returns:
: The validated verify_ssl value.

#### verify_ssl *: bool | str*

## zenml.zen_stores.sql_zen_store module

SQL Zen Store implementation.

### *class* zenml.zen_stores.sql_zen_store.SQLDatabaseDriver(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

SQL database drivers supported by the SQL ZenML store.

#### MYSQL *= 'mysql'*

#### SQLITE *= 'sqlite'*

### *class* zenml.zen_stores.sql_zen_store.SqlZenStore(skip_default_registrations: bool = False, \*, config: [SqlZenStoreConfiguration](#zenml.zen_stores.sql_zen_store.SqlZenStoreConfiguration), skip_migrations: bool = False)

Bases: [`BaseZenStore`](#zenml.zen_stores.base_zen_store.BaseZenStore)

Store Implementation that uses SQL database backend.

Attributes:
: config: The configuration of the SQL ZenML store.
  skip_migrations: Whether to skip migrations when initializing the store.
  TYPE: The type of the store.
  CONFIG_TYPE: The type of the store configuration.
  \_engine: The SQLAlchemy engine.

#### CONFIG_TYPE

alias of [`SqlZenStoreConfiguration`](#zenml.zen_stores.sql_zen_store.SqlZenStoreConfiguration)

#### TYPE *: ClassVar[[StoreType](zenml.md#zenml.enums.StoreType)]* *= 'sql'*

#### activate_server(request: [ServerActivationRequest](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerActivationRequest)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse) | None

Activate the server and optionally create the default admin user.

Args:
: request: The server activation request.

Returns:
: The default admin user that was created, if any.

Raises:
: IllegalOperationError: If the server is already active.

#### *property* alembic *: [Alembic](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.alembic.Alembic)*

The Alembic wrapper.

Returns:
: The Alembic wrapper.

Raises:
: ValueError: If the store is not initialized.

#### backup_database(strategy: [DatabaseBackupStrategy](zenml.md#zenml.enums.DatabaseBackupStrategy) | None = None, location: str | None = None, overwrite: bool = False) → Tuple[str, Any]

Backup the database.

Args:
: strategy: Custom backup strategy to use. If not set, the backup
  : strategy from the store configuration will be used.
  <br/>
  location: Custom target location to backup the database to. If not
  : set, the configured backup location will be used. Depending on
    the backup strategy, this can be a file path or a database name.
  <br/>
  overwrite: Whether to overwrite an existing backup if it exists.
  : If set to False, the existing backup will be reused.

Returns:
: The location where the database was backed up to and an accompanying
  user-friendly message that describes the backup location, or None
  if no backup was created (i.e. because the backup already exists).

Raises:
: ValueError: If the backup database name is not set when the backup
  : database is requested or if the backup strategy is invalid.

#### backup_secrets(ignore_errors: bool = True, delete_secrets: bool = False) → None

Backs up all secrets to the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the backup
  : process and attempt to backup all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully backed up from the primary secrets store. Setting
    this flag effectively moves all secrets from the primary secrets
    store to the backup secrets store.

# noqa: DAR401
Raises:

> BackupSecretsStoreNotConfiguredError: if no backup secrets store is
> : configured.

#### *property* backup_secrets_store *: [BaseSecretsStore](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore) | None*

The backup secrets store associated with this store.

Returns:
: The backup secrets store associated with this store.

#### cleanup_database_backup(strategy: [DatabaseBackupStrategy](zenml.md#zenml.enums.DatabaseBackupStrategy) | None = None, location: Any | None = None) → None

Delete the database backup.

Args:
: strategy: Custom backup strategy to use. If not set, the backup
  : strategy from the store configuration will be used.
  <br/>
  location: Custom target location to delete the database backup
  : from. If not set, the configured backup location will be used.
    Depending on the backup strategy, this can be a file path or a
    database name.

Raises:
: ValueError: If the backup database name is not set when the backup
  : database is requested.

#### config *: [SqlZenStoreConfiguration](#zenml.zen_stores.sql_zen_store.SqlZenStoreConfiguration)*

#### count_pipelines(filter_model: [PipelineFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineFilter) | None) → int

Count all pipelines.

Args:
: filter_model: The filter model to use for counting pipelines.

Returns:
: The number of pipelines.

#### count_runs(filter_model: [PipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunFilter) | None) → int

Count all pipeline runs.

Args:
: filter_model: The filter model to filter the runs.

Returns:
: The number of pipeline runs.

#### count_stack_components(filter_model: [ComponentFilter](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentFilter) | None = None) → int

Count all components.

Args:
: filter_model: The filter model to use for counting components.

Returns:
: The number of components.

#### count_stacks(filter_model: [StackFilter](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackFilter) | None) → int

Count all stacks.

Args:
: filter_model: The filter model to filter the stacks.

Returns:
: The number of stacks.

#### create_action(action: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Create an action.

Args:
: action: The action to create.

Returns:
: The created action.

#### create_api_key(service_account_id: UUID, api_key: [APIKeyRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Create a new API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : create the API key.
  <br/>
  api_key: The API key to create.

Returns:
: The created API key.

Raises:
: EntityExistsError: If an API key with the same name is already
  : configured for the same service account.

#### create_artifact(artifact: [ArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactRequest)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Creates a new artifact.

Args:
: artifact: The artifact to create.

Returns:
: The newly created artifact.

Raises:
: EntityExistsError: If an artifact with the same name already exists.

#### create_artifact_version(artifact_version: [ArtifactVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionRequest)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Creates an artifact version.

Args:
: artifact_version: The artifact version to create.

Returns:
: The created artifact version.

Raises:
: EntityExistsError: if an artifact with the same name and version
  : already exists.

#### create_authorized_device(device: [OAuthDeviceInternalRequest](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalRequest)) → [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse)

Creates a new OAuth 2.0 authorized device.

Args:
: device: The device to be created.

Returns:
: The newly created device.

Raises:
: EntityExistsError: If a device for the same client ID already
  : exists.

#### create_build(build: [PipelineBuildRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildRequest)) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Creates a new build in a workspace.

Args:
: build: The build to create.

Returns:
: The newly created build.

#### create_code_repository(code_repository: [CodeRepositoryRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryRequest)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Creates a new code repository.

Args:
: code_repository: Code repository to be created.

Returns:
: The newly created code repository.

Raises:
: EntityExistsError: If a code repository with the given name already
  : exists.

#### create_deployment(deployment: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest)) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Creates a new deployment in a workspace.

Args:
: deployment: The deployment to create.

Returns:
: The newly created deployment.

#### create_event_source(event_source: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Create an event_source.

Args:
: event_source: The event_source to create.

Returns:
: The created event_source.

#### create_flavor(flavor: [FlavorRequest](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorRequest)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Creates a new stack component flavor.

Args:
: flavor: The stack component flavor to create.

Returns:
: The newly created flavor.

Raises:
: EntityExistsError: If a flavor with the same name and type
  : is already owned by this user in this workspace.
  <br/>
  ValueError: In case the config_schema string exceeds the max length.

#### create_model(model: [ModelRequest](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelRequest)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Creates a new model.

Args:
: model: the Model to be created.

Returns:
: The newly created model.

Raises:
: EntityExistsError: If a workspace with the given name already exists.

#### create_model_version(model_version: [ModelVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionRequest)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Creates a new model version.

Args:
: model_version: the Model Version to be created.

Returns:
: The newly created model version.

Raises:
: ValueError: If number is not None during model version creation.
  EntityExistsError: If a workspace with the given name already exists.

#### create_model_version_artifact_link(model_version_artifact_link: [ModelVersionArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest)) → [ModelVersionArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse)

Creates a new model version link.

Args:
: model_version_artifact_link: the Model Version to Artifact Link
  : to be created.

Returns:
: The newly created model version to artifact link.

#### create_model_version_pipeline_run_link(model_version_pipeline_run_link: [ModelVersionPipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest)) → [ModelVersionPipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse)

Creates a new model version to pipeline run link.

Args:
: model_version_pipeline_run_link: the Model Version to Pipeline Run
  : Link to be created.

Returns:
: - If Model Version to Pipeline Run Link already exists - returns
    : the existing link.
  - Otherwise, returns the newly created model version to pipeline
    : run link.

#### create_pipeline(pipeline: [PipelineRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineRequest)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Creates a new pipeline in a workspace.

Args:
: pipeline: The pipeline to create.

Returns:
: The newly created pipeline.

Raises:
: EntityExistsError: If an identical pipeline already exists.

#### create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Creates a pipeline run.

Args:
: pipeline_run: The pipeline run to create.

Returns:
: The created pipeline run.

Raises:
: EntityExistsError: If a run with the same name already exists.

#### create_run_metadata(run_metadata: [RunMetadataRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataRequest)) → List[[RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)]

Creates run metadata.

Args:
: run_metadata: The run metadata to create.

Returns:
: The created run metadata.

#### create_run_step(step_run: [StepRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunRequest)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Creates a step run.

Args:
: step_run: The step run to create.

Returns:
: The created step run.

Raises:
: EntityExistsError: if the step run already exists.
  KeyError: if the pipeline run doesn’t exist.

#### create_run_template(template: [RunTemplateRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateRequest)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Create a new run template.

Args:
: template: The template to create.

Returns:
: The newly created template.

Raises:
: EntityExistsError: If a template with the same name already exists.
  ValueError: If the source deployment does not exist or does not
  <br/>
  > have an associated build.

#### create_schedule(schedule: [ScheduleRequest](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleRequest)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Creates a new schedule.

Args:
: schedule: The schedule to create.

Returns:
: The newly created schedule.

#### create_secret(secret: [SecretRequest](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretRequest)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Creates a new secret.

The new secret is also validated against the scoping rules enforced in
the secrets store:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret: The secret to create.

Returns:
: The newly created secret.

Raises:
: EntityExistsError: If a secret with the same name already exists in
  : the same scope.

#### create_service(service: [ServiceRequest](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceRequest)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Create a new service.

Args:
: service: The service to create.

Returns:
: The newly created service.

#### create_service_account(service_account: [ServiceAccountRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountRequest)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Creates a new service account.

Args:
: service_account: Service account to be created.

Returns:
: The newly created service account.

Raises:
: EntityExistsError: If a user or service account with the given name
  : already exists.

#### create_service_connector(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Creates a new service connector.

Args:
: service_connector: Service connector to be created.

Returns:
: The newly created service connector.

Raises:
: Exception: If anything goes wrong during the creation of the
  : service connector.

#### create_stack(stack: [StackRequest](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackRequest)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Register a full stack.

Args:
: stack: The full stack configuration.

Returns:
: The registered stack.

Raises:
: ValueError: If the full stack creation fails, due to the corrupted
  : input.
  <br/>
  Exception: If the full stack creation fails, due to unforeseen
  : errors.

#### create_stack_component(component: [ComponentRequest](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentRequest)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Create a stack component.

Args:
: component: The stack component to create.

Returns:
: The created stack component.

Raises:
: KeyError: if the stack component references a non-existent
  : connector.

#### create_tag(tag: [TagRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagRequest)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Creates a new tag.

Args:
: tag: the tag to be created.

Returns:
: The newly created tag.

Raises:
: EntityExistsError: If a tag with the given name already exists.

#### create_tag_resource(tag_resource: [TagResourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceRequest)) → [TagResourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceResponse)

Creates a new tag resource relationship.

Args:
: tag_resource: the tag resource relationship to be created.

Returns:
: The newly created tag resource relationship.

Raises:
: EntityExistsError: If a tag resource relationship with the given
  : configuration already exists.

#### create_trigger(trigger: [TriggerRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerRequest)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Creates a new trigger.

Args:
: trigger: Trigger to be created.

Returns:
: The newly created trigger.

#### create_trigger_execution(trigger_execution: [TriggerExecutionRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionRequest)) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Create a trigger execution.

Args:
: trigger_execution: The trigger execution to create.

Returns:
: The created trigger execution.

#### create_user(user: [UserRequest](zenml.models.v2.core.md#zenml.models.v2.core.user.UserRequest)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Creates a new user.

Args:
: user: User to be created.

Returns:
: The newly created user.

Raises:
: EntityExistsError: If a user or service account with the given name
  : already exists.

#### create_workspace(workspace: [WorkspaceRequest](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceRequest)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Creates a new workspace.

Args:
: workspace: The workspace to create.

Returns:
: The newly created workspace.

Raises:
: EntityExistsError: If a workspace with the given name already exists.

#### delete_action(action_id: UUID) → None

Delete an action.

Args:
: action_id: The ID of the action to delete.

Raises:
: IllegalOperationError: If the action can’t be deleted
  : because it’s used by triggers.

#### delete_all_model_version_artifact_links(model_version_id: UUID, only_links: bool = True) → None

Deletes all model version to artifact links.

Args:
: model_version_id: ID of the model version containing the link.
  only_links: Whether to only delete the link to the artifact.

#### delete_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID) → None

Delete an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : delete the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to delete.

#### delete_artifact(artifact_id: UUID) → None

Deletes an artifact.

Args:
: artifact_id: The ID of the artifact to delete.

Raises:
: KeyError: if the artifact doesn’t exist.

#### delete_artifact_version(artifact_version_id: UUID) → None

Deletes an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to delete.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### delete_authorized_device(device_id: UUID) → None

Deletes an OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to delete.

Raises:
: KeyError: If no device with the given ID exists.

#### delete_build(build_id: UUID) → None

Deletes a build.

Args:
: build_id: The ID of the build to delete.

Raises:
: KeyError: if the build doesn’t exist.

#### delete_code_repository(code_repository_id: UUID) → None

Deletes a code repository.

Args:
: code_repository_id: The ID of the code repository to delete.

Raises:
: KeyError: If no code repository with the given ID exists.

#### delete_deployment(deployment_id: UUID) → None

Deletes a deployment.

Args:
: deployment_id: The ID of the deployment to delete.

Raises:
: KeyError: If the deployment doesn’t exist.

#### delete_event_source(event_source_id: UUID) → None

Delete an event_source.

Args:
: event_source_id: The ID of the event_source to delete.

Raises:
: KeyError: if the event_source doesn’t exist.
  IllegalOperationError: If the event source can’t be deleted
  <br/>
  > because it’s used by triggers.

#### delete_expired_authorized_devices() → None

Deletes all expired OAuth 2.0 authorized devices.

#### delete_flavor(flavor_id: UUID) → None

Delete a flavor.

Args:
: flavor_id: The id of the flavor to delete.

Raises:
: KeyError: if the flavor doesn’t exist.
  IllegalOperationError: if the flavor is used by a stack component.

#### delete_model(model_name_or_id: str | UUID) → None

Deletes a model.

Args:
: model_name_or_id: name or id of the model to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### delete_model_version(model_version_id: UUID) → None

Deletes a model version.

Args:
: model_version_id: name or id of the model version to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### delete_model_version_artifact_link(model_version_id: UUID, model_version_artifact_link_name_or_id: str | UUID) → None

Deletes a model version to artifact link.

Args:
: model_version_id: ID of the model version containing the link.
  model_version_artifact_link_name_or_id: name or ID of the model
  <br/>
  > version to artifact link to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### delete_model_version_pipeline_run_link(model_version_id: UUID, model_version_pipeline_run_link_name_or_id: str | UUID) → None

Deletes a model version to pipeline run link.

Args:
: model_version_id: name or ID of the model version containing the
  : link.
  <br/>
  model_version_pipeline_run_link_name_or_id: name or ID of the model
  : version to pipeline run link to be deleted.

Raises:
: KeyError: specified ID not found.

#### delete_pipeline(pipeline_id: UUID) → None

Deletes a pipeline.

Args:
: pipeline_id: The ID of the pipeline to delete.

Raises:
: KeyError: if the pipeline doesn’t exist.

#### delete_run(run_id: UUID) → None

Deletes a pipeline run.

Args:
: run_id: The ID of the pipeline run to delete.

Raises:
: KeyError: if the pipeline run doesn’t exist.

#### delete_run_template(template_id: UUID) → None

Delete a run template.

Args:
: template_id: The ID of the template to delete.

Raises:
: KeyError: If the template does not exist.

#### delete_schedule(schedule_id: UUID) → None

Deletes a schedule.

Args:
: schedule_id: The ID of the schedule to delete.

Raises:
: KeyError: if the schedule doesn’t exist.

#### delete_secret(secret_id: UUID) → None

Delete a secret.

Args:
: secret_id: The id of the secret to delete.

Raises:
: KeyError: if the secret doesn’t exist.

#### delete_service(service_id: UUID) → None

Delete a service.

Args:
: service_id: The ID of the service to delete.

Raises:
: KeyError: if the service doesn’t exist.

#### delete_service_account(service_account_name_or_id: str | UUID) → None

Delete a service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to delete.

Raises:
: IllegalOperationError: if the service account has already been used
  : to create other resources.

#### delete_service_connector(service_connector_id: UUID) → None

Deletes a service connector.

Args:
: service_connector_id: The ID of the service connector to delete.

Raises:
: KeyError: If no service connector with the given ID exists.
  IllegalOperationError: If the service connector is still referenced
  <br/>
  > by one or more stack components.

#### delete_stack(stack_id: UUID) → None

Delete a stack.

Args:
: stack_id: The ID of the stack to delete.

Raises:
: KeyError: if the stack doesn’t exist.
  IllegalOperationError: if the stack is a default stack.

#### delete_stack_component(component_id: UUID) → None

Delete a stack component.

Args:
: component_id: The id of the stack component to delete.

Raises:
: KeyError: if the stack component doesn’t exist.
  IllegalOperationError: if the stack component is part of one or
  <br/>
  > more stacks, or if it’s a default stack component.

#### delete_tag(tag_name_or_id: str | UUID) → None

Deletes a tag.

Args:
: tag_name_or_id: name or id of the tag to delete.

Raises:
: KeyError: specified ID or name not found.

#### delete_tag_resource(tag_id: UUID, resource_id: UUID, resource_type: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes)) → None

Deletes a tag resource relationship.

Args:
: tag_id: The ID of the tag to delete.
  resource_id: The ID of the resource to delete.
  resource_type: The type of the resource to delete.

Raises:
: KeyError: specified ID not found.

#### delete_trigger(trigger_id: UUID) → None

Delete a trigger.

Args:
: trigger_id: The ID of the trigger to delete.

Raises:
: KeyError: if the trigger doesn’t exist.

#### delete_trigger_execution(trigger_execution_id: UUID) → None

Delete a trigger execution.

Args:
: trigger_execution_id: The ID of the trigger execution to delete.

Raises:
: KeyError: If the trigger execution doesn’t exist.

#### delete_user(user_name_or_id: str | UUID) → None

Deletes a user.

Args:
: user_name_or_id: The name or the ID of the user to delete.

Raises:
: IllegalOperationError: If the user is the default user account or
  : if the user already owns resources.

#### delete_workspace(workspace_name_or_id: str | UUID) → None

Deletes a workspace.

Args:
: workspace_name_or_id: Name or ID of the workspace to delete.

Raises:
: IllegalOperationError: If the workspace is the default workspace.

#### *property* engine *: Engine*

The SQLAlchemy engine.

Returns:
: The SQLAlchemy engine.

Raises:
: ValueError: If the store is not initialized.

#### entity_exists(entity_id: UUID, schema_class: Type[AnySchema]) → bool

Check whether an entity exists in the database.

Args:
: entity_id: The ID of the entity to check.
  schema_class: The schema class.

Returns:
: If the entity exists.

#### *classmethod* filter_and_paginate(session: Session, query: Select | SelectOfScalar, table: Type[AnySchema], filter_model: [BaseFilter](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter), custom_schema_to_model_conversion: Callable[[...], AnyResponse] | None = None, custom_fetch: Callable[[Session, Select | SelectOfScalar, [BaseFilter](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)], Sequence[Any]] | None = None, hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[AnyResponse]

Given a query, return a Page instance with a list of filtered Models.

Args:
: session: The SQLModel Session
  query: The query to execute
  table: The table to select from
  filter_model: The filter to use, including pagination and sorting
  custom_schema_to_model_conversion: Callable to convert the schema
  <br/>
  > into a model. This is used if the Model contains additional
  > data that is not explicitly stored as a field or relationship
  > on the model.
  <br/>
  custom_fetch: Custom callable to use to fetch items from the
  : database for a given query. This is used if the items fetched
    from the database need to be processed differently (e.g. to
    perform additional filtering). The callable should take a
    Session, a Select query and a BaseFilterModel filter as
    arguments and return a List of items.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The Domain Model representation of the DB resource

Raises:
: ValueError: if the filtered page number is out of bounds.
  RuntimeError: if the schema does not have a to_model method.

#### get_action(action_id: UUID, hydrate: bool = True) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Get an action by ID.

Args:
: action_id: The ID of the action to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The action.

#### get_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, hydrate: bool = True) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Get an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to fetch
  : the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The API key with the given ID.

#### get_artifact(artifact_id: UUID, hydrate: bool = True) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Gets an artifact.

Args:
: artifact_id: The ID of the artifact to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact.

Raises:
: KeyError: if the artifact doesn’t exist.

#### get_artifact_version(artifact_version_id: UUID, hydrate: bool = True) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Gets an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact version.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### get_artifact_visualization(artifact_visualization_id: UUID, hydrate: bool = True) → [ArtifactVisualizationResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Gets an artifact visualization.

Args:
: artifact_visualization_id: The ID of the artifact visualization to
  : get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The artifact visualization.

Raises:
: KeyError: if the code reference doesn’t exist.

#### get_auth_user(user_name_or_id: str | UUID) → [UserAuthModel](zenml.models.v2.misc.md#zenml.models.v2.misc.user_auth.UserAuthModel)

Gets the auth model to a specific user.

Args:
: user_name_or_id: The name or ID of the user to get.

Returns:
: The requested user, if it was found.

#### get_authorized_device(device_id: UUID, hydrate: bool = True) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Gets a specific OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested device, if it was found.

Raises:
: KeyError: If no device with the given ID exists.

#### get_build(build_id: UUID, hydrate: bool = True) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Get a build with a given ID.

Args:
: build_id: ID of the build.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The build.

Raises:
: KeyError: If the build does not exist.

#### get_code_reference(code_reference_id: UUID, hydrate: bool = True) → [CodeReferenceResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Gets a code reference.

Args:
: code_reference_id: The ID of the code reference to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The code reference.

Raises:
: KeyError: if the code reference doesn’t exist.

#### get_code_repository(code_repository_id: UUID, hydrate: bool = True) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Gets a specific code repository.

Args:
: code_repository_id: The ID of the code repository to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested code repository, if it was found.

Raises:
: KeyError: If no code repository with the given ID exists.

#### get_deployment(deployment_id: UUID, hydrate: bool = True) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Get a deployment with a given ID.

Args:
: deployment_id: ID of the deployment.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The deployment.

Raises:
: KeyError: If the deployment does not exist.

#### get_deployment_id() → UUID

Get the ID of the deployment.

Returns:
: The ID of the deployment.

Raises:
: KeyError: If the deployment ID could not be loaded from the
  : database.

#### get_entity_by_id(entity_id: UUID, schema_class: Type[AnySchema]) → AnyIdentifiedResponse | None

Get an entity by ID.

Args:
: entity_id: The ID of the entity to get.
  schema_class: The schema class.

Raises:
: RuntimeError: If the schema to model conversion failed.

Returns:
: The entity if it exists, None otherwise

#### get_event_source(event_source_id: UUID, hydrate: bool = True) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Get an event_source by ID.

Args:
: event_source_id: The ID of the event_source to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The event_source.

#### get_flavor(flavor_id: UUID, hydrate: bool = True) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Get a flavor by ID.

Args:
: flavor_id: The ID of the flavor to fetch.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component flavor.

Raises:
: KeyError: if the stack component flavor doesn’t exist.

#### get_internal_api_key(api_key_id: UUID, hydrate: bool = True) → [APIKeyInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalResponse)

Get internal details for an API key by its unique ID.

Args:
: api_key_id: The ID of the API key to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The internal details for the API key with the given ID.

Raises:
: KeyError: if the API key doesn’t exist.

#### get_internal_authorized_device(device_id: UUID | None = None, client_id: UUID | None = None, hydrate: bool = True) → [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse)

Gets a specific OAuth 2.0 authorized device for internal use.

Args:
: client_id: The client ID of the device to get.
  device_id: The ID of the device to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested device, if it was found.

Raises:
: KeyError: If no device with the given client ID exists.
  ValueError: If neither device ID nor client ID are provided.

#### get_logs(logs_id: UUID, hydrate: bool = True) → [LogsResponse](zenml.models.v2.core.md#zenml.models.v2.core.logs.LogsResponse)

Gets logs with the given ID.

Args:
: logs_id: The ID of the logs to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The logs.

Raises:
: KeyError: if the logs doesn’t exist.

#### get_model(model_name_or_id: str | UUID, hydrate: bool = True) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Get an existing model.

Args:
: model_name_or_id: name or id of the model to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Raises:
: KeyError: specified ID or name not found.

Returns:
: The model of interest.

#### get_model_version(model_version_id: UUID, hydrate: bool = True) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get an existing model version.

Args:
: model_version_id: name, id, stage or number of the model version to
  : be retrieved. If skipped - latest is retrieved.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The model version of interest.

Raises:
: KeyError: specified ID or name not found.

#### get_onboarding_state() → List[str]

Get the server onboarding state.

Returns:
: The server onboarding state.

#### get_or_create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest), pre_creation_hook: Callable[[], None] | None = None) → Tuple[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse), bool]

Gets or creates a pipeline run.

If a run with the same ID or name already exists, it is returned.
Otherwise, a new run is created.

Args:
: pipeline_run: The pipeline run to get or create.
  pre_creation_hook: Optional function to run before creating the
  <br/>
  > pipeline run.

# noqa: DAR401
Raises:

> ValueError: If the request does not contain an orchestrator run ID.
> EntityExistsError: If a run with the same name already exists.
> RuntimeError: If the run fetching failed unexpectedly.

Returns:
: The pipeline run, and a boolean indicating whether the run was
  created or not.

#### get_pipeline(pipeline_id: UUID, hydrate: bool = True) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Get a pipeline with a given ID.

Args:
: pipeline_id: ID of the pipeline.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline.

Raises:
: KeyError: if the pipeline does not exist.

#### get_run(run_name_or_id: str | UUID, hydrate: bool = True) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Gets a pipeline run.

Args:
: run_name_or_id: The name or ID of the pipeline run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline run.

#### get_run_metadata(run_metadata_id: UUID, hydrate: bool = True) → [RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Gets run metadata with the given ID.

Args:
: run_metadata_id: The ID of the run metadata to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The run metadata.

Raises:
: KeyError: if the run metadata doesn’t exist.

#### get_run_step(step_run_id: UUID, hydrate: bool = True) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Get a step run by ID.

Args:
: step_run_id: The ID of the step run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The step run.

Raises:
: KeyError: if the step run doesn’t exist.

#### get_run_template(template_id: UUID, hydrate: bool = True) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Get a run template with a given ID.

Args:
: template_id: ID of the template.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The template.

Raises:
: KeyError: If the template does not exist.

#### get_schedule(schedule_id: UUID, hydrate: bool = True) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Get a schedule with a given ID.

Args:
: schedule_id: ID of the schedule.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The schedule.

Raises:
: KeyError: if the schedule does not exist.

#### get_secret(secret_id: UUID, hydrate: bool = True) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Get a secret by ID.

Args:
: secret_id: The ID of the secret to fetch.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The secret.

Raises:
: KeyError: if the secret doesn’t exist.

#### get_server_settings(hydrate: bool = True) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Get the server settings.

Args:
: hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The server settings.

#### get_service(service_id: UUID, hydrate: bool = True) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Get a service.

Args:
: service_id: The ID of the service to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The service.

Raises:
: KeyError: if the service doesn’t exist.

#### get_service_account(service_account_name_or_id: str | UUID, hydrate: bool = True) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Gets a specific service account.

Raises a KeyError in case a service account with that id does not exist.

Args:
: service_account_name_or_id: The name or ID of the service account to
  : get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The requested service account, if it was found.

#### get_service_connector(service_connector_id: UUID, hydrate: bool = True) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Gets a specific service connector.

Args:
: service_connector_id: The ID of the service connector to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested service connector, if it was found.

Raises:
: KeyError: If no service connector with the given ID exists.

#### get_service_connector_client(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Get a service connector client for a service connector and given resource.

Args:
: service_connector_id: The ID of the base service connector to use.
  resource_type: The type of resource to get a client for.
  resource_id: The ID of the resource to get a client for.

Returns:
: A service connector client that can be used to access the given
  resource.

#### get_service_connector_type(connector_type: str) → [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)

Returns the requested service connector type.

Args:
: connector_type: the service connector type identifier.

Returns:
: The requested service connector type.

#### get_stack(stack_id: UUID, hydrate: bool = True) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Get a stack by its unique ID.

Args:
: stack_id: The ID of the stack to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack with the given ID.

Raises:
: KeyError: if the stack doesn’t exist.

#### get_stack_component(component_id: UUID, hydrate: bool = True) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Get a stack component by ID.

Args:
: component_id: The ID of the stack component to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component.

Raises:
: KeyError: if the stack component doesn’t exist.

#### get_stack_deployment_config(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None) → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the cloud provider console URL and configuration needed to deploy the ZenML stack.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.

Raises:
: NotImplementedError: Stack deployments are not supported by the
  : local ZenML deployment.

#### get_stack_deployment_info(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)) → [StackDeploymentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentInfo)

Get information about a stack deployment provider.

Args:
: provider: The stack deployment provider.

Raises:
: NotImplementedError: Stack deployments are not supported by the
  : local ZenML deployment.

#### get_stack_deployment_stack(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None, date_start: datetime | None = None) → [DeployedStack](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.DeployedStack) | None

Return a matching ZenML stack that was deployed and registered.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.
  date_start: The date when the deployment started.

Raises:
: NotImplementedError: Stack deployments are not supported by the
  : local ZenML deployment.

#### get_store_info() → [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)

Get information about the store.

Returns:
: Information about the store.

#### get_tag(tag_name_or_id: str | UUID, hydrate: bool = True) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Get an existing tag.

Args:
: tag_name_or_id: name or id of the tag to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The tag of interest.

Raises:
: KeyError: specified ID or name not found.

#### get_trigger(trigger_id: UUID, hydrate: bool = True) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Get a trigger by its unique ID.

Args:
: trigger_id: The ID of the trigger to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger with the given ID.

Raises:
: KeyError: If the trigger doesn’t exist.

#### get_trigger_execution(trigger_execution_id: UUID, hydrate: bool = True) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Get an trigger execution by ID.

Args:
: trigger_execution_id: The ID of the trigger execution to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger execution.

Raises:
: KeyError: If the trigger execution doesn’t exist.

#### get_user(user_name_or_id: str | UUID | None = None, include_private: bool = False, hydrate: bool = True) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Gets a specific user, when no id is specified the active user is returned.

# noqa: DAR401
# noqa: DAR402

Raises a KeyError in case a user with that name or id does not exist.

For backwards-compatibility reasons, this method can also be called
to fetch service accounts by their ID.

Args:
: user_name_or_id: The name or ID of the user to get.
  include_private: Whether to include private user information
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested user, if it was found.

Raises:
: KeyError: If the user does not exist.

#### get_workspace(workspace_name_or_id: str | UUID, hydrate: bool = True) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Get an existing workspace by name or ID.

Args:
: workspace_name_or_id: Name or ID of the workspace to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested workspace if one was found.

#### list_actions(action_filter_model: [ActionFilter](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ActionResponse](zenml.models.md#zenml.models.ActionResponse)]

List all actions matching the given filter criteria.

Args:
: action_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of actions matching the filter criteria.

#### list_api_keys(service_account_id: UUID, filter_model: [APIKeyFilter](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[APIKeyResponse](zenml.models.md#zenml.models.APIKeyResponse)]

List all API keys for a service account matching the given filter criteria.

Args:
: service_account_id: The ID of the service account for which to list
  : the API keys.
  <br/>
  filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all API keys matching the filter criteria.

#### list_artifact_versions(artifact_version_filter_model: [ArtifactVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]

List all artifact versions matching the given filter criteria.

Args:
: artifact_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifact versions matching the filter criteria.

#### list_artifacts(filter_model: [ArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactResponse](zenml.models.md#zenml.models.ArtifactResponse)]

List all artifacts matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifacts matching the filter criteria.

#### list_authorized_devices(filter_model: [OAuthDeviceFilter](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[OAuthDeviceResponse](zenml.models.md#zenml.models.OAuthDeviceResponse)]

List all OAuth 2.0 authorized devices for a user.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all matching OAuth 2.0 authorized devices.

#### list_builds(build_filter_model: [PipelineBuildFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse)]

List all builds matching the given filter criteria.

Args:
: build_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all builds matching the filter criteria.

#### list_code_repositories(filter_model: [CodeRepositoryFilter](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[CodeRepositoryResponse](zenml.models.md#zenml.models.CodeRepositoryResponse)]

List all code repositories.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all code repositories.

#### list_deployments(deployment_filter_model: [PipelineDeploymentFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)]

List all deployments matching the given filter criteria.

Args:
: deployment_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all deployments matching the filter criteria.

#### list_event_sources(event_source_filter_model: [EventSourceFilter](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[EventSourceResponse](zenml.models.md#zenml.models.EventSourceResponse)]

List all event_sources matching the given filter criteria.

Args:
: event_source_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all event_sources matching the filter criteria.

#### list_flavors(flavor_filter_model: [FlavorFilter](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[FlavorResponse](zenml.models.md#zenml.models.FlavorResponse)]

List all stack component flavors matching the given filter criteria.

Args:
: flavor_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: List of all the stack component flavors matching the given criteria.

#### list_model_version_artifact_links(model_version_artifact_link_filter_model: [ModelVersionArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionArtifactResponse](zenml.models.md#zenml.models.ModelVersionArtifactResponse)]

Get all model version to artifact links by filter.

Args:
: model_version_artifact_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to artifact links.

#### list_model_version_pipeline_run_links(model_version_pipeline_run_link_filter_model: [ModelVersionPipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionPipelineRunResponse](zenml.models.md#zenml.models.ModelVersionPipelineRunResponse)]

Get all model version to pipeline run links by filter.

Args:
: model_version_pipeline_run_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to pipeline run links.

#### list_model_versions(model_version_filter_model: [ModelVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionFilter), model_name_or_id: str | UUID | None = None, hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionResponse](zenml.models.md#zenml.models.ModelVersionResponse)]

Get all model versions by filter.

Args:
: model_name_or_id: name or id of the model containing the model
  : versions.
  <br/>
  model_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model versions.

#### list_models(model_filter_model: [ModelFilter](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelResponse](zenml.models.md#zenml.models.ModelResponse)]

Get all models by filter.

Args:
: model_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all models.

#### list_pipelines(pipeline_filter_model: [PipelineFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineResponse](zenml.models.md#zenml.models.PipelineResponse)]

List all pipelines matching the given filter criteria.

Args:
: pipeline_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipelines matching the filter criteria.

#### list_run_metadata(run_metadata_filter_model: [RunMetadataFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]

List run metadata.

Args:
: run_metadata_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The run metadata.

#### list_run_steps(step_run_filter_model: [StepRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)]

List all step runs matching the given filter criteria.

Args:
: step_run_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all step runs matching the filter criteria.

#### list_run_templates(template_filter_model: [RunTemplateFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunTemplateResponse](zenml.models.md#zenml.models.RunTemplateResponse)]

List all run templates matching the given filter criteria.

Args:
: template_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all templates matching the filter criteria.

#### list_runs(runs_filter_model: [PipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]

List all pipeline runs matching the given filter criteria.

Args:
: runs_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipeline runs matching the filter criteria.

#### list_schedules(schedule_filter_model: [ScheduleFilter](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse)]

List all schedules in the workspace.

Args:
: schedule_filter_model: All filter parameters including pagination
  : params
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of schedules.

#### list_secrets(secret_filter_model: [SecretFilter](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[SecretResponse](zenml.models.md#zenml.models.SecretResponse)]

List all secrets matching the given filter criteria.

Note that returned secrets do not include any secret values. To fetch
the secret values, use get_secret.

Args:
: secret_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all secrets matching the filter criteria, with pagination
  information and sorted according to the filter criteria. The
  returned secrets do not include any secret values, only metadata. To
  fetch the secret values, use get_secret individually with each
  secret.

#### list_service_accounts(filter_model: [ServiceAccountFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceAccountResponse](zenml.models.md#zenml.models.ServiceAccountResponse)]

List all service accounts.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of filtered service accounts.

#### list_service_connector_resources(workspace_name_or_id: str | UUID, connector_type: str | None = None, resource_type: str | None = None, resource_id: str | None = None, filter_model: [ServiceConnectorFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorFilter) | None = None) → List[[ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)]

List resources that can be accessed by service connectors.

Args:
: workspace_name_or_id: The name or ID of the workspace to scope to.
  connector_type: The type of service connector to scope to.
  resource_type: The type of resource to scope to.
  resource_id: The ID of the resource to scope to.
  filter_model: Optional filter model to use when fetching service
  <br/>
  > connectors.

Returns:
: The matching list of resources that available service
  connectors have access to.

#### list_service_connector_types(connector_type: str | None = None, resource_type: str | None = None, auth_method: str | None = None) → List[[ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)]

Get a list of service connector types.

Args:
: connector_type: Filter by connector type.
  resource_type: Filter by resource type.
  auth_method: Filter by authentication method.

Returns:
: List of service connector types.

#### list_service_connectors(filter_model: [ServiceConnectorFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse)]

List all service connectors.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all service connectors.

#### list_services(filter_model: [ServiceFilter](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)]

List all services matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all services matching the filter criteria.

#### list_stack_components(component_filter_model: [ComponentFilter](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]

List all stack components matching the given filter criteria.

Args:
: component_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stack components matching the filter criteria.

#### list_stacks(stack_filter_model: [StackFilter](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StackResponse](zenml.models.md#zenml.models.StackResponse)]

List all stacks matching the given filter criteria.

Args:
: stack_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stacks matching the filter criteria.

#### list_tags(tag_filter_model: [TagFilter](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TagResponse](zenml.models.md#zenml.models.TagResponse)]

Get all tags by filter.

Args:
: tag_filter_model: All filter parameters including pagination params.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: A page of all tags.

#### list_trigger_executions(trigger_execution_filter_model: [TriggerExecutionFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)]

List all trigger executions matching the given filter criteria.

Args:
: trigger_execution_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all trigger executions matching the filter criteria.

#### list_triggers(trigger_filter_model: [TriggerFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)]

List all trigger matching the given filter criteria.

Args:
: trigger_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all triggers matching the filter criteria.

#### list_users(user_filter_model: [UserFilter](zenml.models.v2.core.md#zenml.models.v2.core.user.UserFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[UserResponse](zenml.models.md#zenml.models.UserResponse)]

List all users.

Args:
: user_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all users.

#### list_workspaces(workspace_filter_model: [WorkspaceFilter](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)]

List all workspace matching the given filter criteria.

Args:
: workspace_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all workspace matching the filter criteria.

#### migrate_database() → None

Migrate the database to the head as defined by the python package.

Raises:
: RuntimeError: If the database exists and is not empty but has never
  : been migrated with alembic before.

#### *property* migration_utils *: [MigrationUtils](zenml.zen_stores.migrations.md#zenml.zen_stores.migrations.utils.MigrationUtils)*

The migration utils.

Returns:
: The migration utils.

Raises:
: ValueError: If the store is not initialized.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=SqlZenStoreConfiguration, required=True), 'skip_migrations': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### prune_artifact_versions(only_versions: bool = True) → None

Prunes unused artifact versions and their artifacts.

Args:
: only_versions: Only delete artifact versions, keeping artifacts

#### restore_database(strategy: [DatabaseBackupStrategy](zenml.md#zenml.enums.DatabaseBackupStrategy) | None = None, location: Any | None = None, cleanup: bool = False) → None

Restore the database.

Args:
: strategy: Custom backup strategy to use. If not set, the backup
  : strategy from the store configuration will be used.
  <br/>
  location: Custom target location to restore the database from. If
  : not set, the configured backup location will be used. Depending
    on the backup strategy, this can be a file path, a database
    name or an in-memory database representation.
  <br/>
  cleanup: Whether to cleanup the backup after restoring the database.

Raises:
: ValueError: If the backup database name is not set when the backup
  : database is requested or if the backup strategy is invalid.

#### restore_secrets(ignore_errors: bool = False, delete_secrets: bool = False) → None

Restore all secrets from the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the
  : restore process and attempt to restore all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully restored from the backup secrets store. Setting
    this flag effectively moves all secrets from the backup secrets
    store to the primary secrets store.

# noqa: DAR401
Raises:

> BackupSecretsStoreNotConfiguredError: if no backup secrets store is
> : configured.

#### rotate_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, rotate_request: [APIKeyRotateRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRotateRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Rotate an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : rotate the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to rotate.
  rotate_request: The rotate request on the API key.

Returns:
: The updated API key.

#### run_template(template_id: UUID, run_configuration: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) | None = None) → NoReturn

Run a template.

Args:
: template_id: The ID of the template to run.
  run_configuration: Configuration for the run.

Raises:
: NotImplementedError: Always.

#### *property* secrets_store *: [BaseSecretsStore](zenml.zen_stores.secrets_stores.md#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore)*

The secrets store associated with this store.

Returns:
: The secrets store associated with this store.

Raises:
: SecretsStoreNotConfiguredError: If no secrets store is configured.

#### skip_migrations *: bool*

#### update_action(action_id: UUID, action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Update an existing action.

Args:
: action_id: The ID of the action to update.
  action_update: The update to be applied to the action.

Returns:
: The updated action.

#### update_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, api_key_update: [APIKeyUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyUpdate)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Update an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to update
  : the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to update.
  api_key_update: The update request on the API key.

Returns:
: The updated API key.

Raises:
: EntityExistsError: if the API key update would result in a name
  : conflict with an existing API key for the same service account.

#### update_artifact(artifact_id: UUID, artifact_update: [ArtifactUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactUpdate)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Updates an artifact.

Args:
: artifact_id: The ID of the artifact to update.
  artifact_update: The update to be applied to the artifact.

Returns:
: The updated artifact.

Raises:
: KeyError: if the artifact doesn’t exist.

#### update_artifact_version(artifact_version_id: UUID, artifact_version_update: [ArtifactVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionUpdate)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Updates an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to update.
  artifact_version_update: The update to be applied to the artifact
  <br/>
  > version.

Returns:
: The updated artifact version.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### update_authorized_device(device_id: UUID, update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Updates an existing OAuth 2.0 authorized device for internal use.

Args:
: device_id: The ID of the device to update.
  update: The update to be applied to the device.

Returns:
: The updated OAuth 2.0 authorized device.

Raises:
: KeyError: If no device with the given ID exists.

#### update_code_repository(code_repository_id: UUID, update: [CodeRepositoryUpdate](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryUpdate)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Updates an existing code repository.

Args:
: code_repository_id: The ID of the code repository to update.
  update: The update to be applied to the code repository.

Returns:
: The updated code repository.

Raises:
: KeyError: If no code repository with the given name exists.

#### update_event_source(event_source_id: UUID, event_source_update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Update an existing event_source.

Args:
: event_source_id: The ID of the event_source to update.
  event_source_update: The update to be applied to the event_source.

Returns:
: The updated event_source.

#### update_flavor(flavor_id: UUID, flavor_update: [FlavorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorUpdate)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Updates an existing user.

Args:
: flavor_id: The id of the flavor to update.
  flavor_update: The update to be applied to the flavor.

Returns:
: The updated flavor.

Raises:
: KeyError: If no flavor with the given id exists.

#### update_internal_api_key(api_key_id: UUID, api_key_update: [APIKeyInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalUpdate)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Update an API key with internal details.

Args:
: api_key_id: The ID of the API key.
  api_key_update: The update request on the API key.

Returns:
: The updated API key.

Raises:
: KeyError: if the API key doesn’t exist.

#### update_internal_authorized_device(device_id: UUID, update: [OAuthDeviceInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalUpdate)) → [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse)

Updates an existing OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to update.
  update: The update to be applied to the device.

Returns:
: The updated OAuth 2.0 authorized device.

Raises:
: KeyError: If no device with the given ID exists.

#### update_model(model_id: UUID, model_update: [ModelUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelUpdate)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Updates an existing model.

Args:
: model_id: UUID of the model to be updated.
  model_update: the Model to be updated.

Raises:
: KeyError: specified ID not found.

Returns:
: The updated model.

#### update_model_version(model_version_id: UUID, model_version_update_model: [ModelVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionUpdate)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get all model versions by filter.

Args:
: model_version_id: The ID of model version to be updated.
  model_version_update_model: The model version to be updated.

Returns:
: An updated model version.

Raises:
: KeyError: If the model version not found
  RuntimeError: If there is a model version with target stage,
  <br/>
  > but force flag is off

#### update_onboarding_state(completed_steps: Set[str]) → None

Update the server onboarding state.

Args:
: completed_steps: Newly completed onboarding steps.

#### update_pipeline(pipeline_id: UUID, pipeline_update: [PipelineUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineUpdate)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Updates a pipeline.

Args:
: pipeline_id: The ID of the pipeline to be updated.
  pipeline_update: The update to be applied.

Returns:
: The updated pipeline.

Raises:
: KeyError: if the pipeline doesn’t exist.

#### update_run(run_id: UUID, run_update: [PipelineRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunUpdate)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Updates a pipeline run.

Args:
: run_id: The ID of the pipeline run to update.
  run_update: The update to be applied to the pipeline run.

Returns:
: The updated pipeline run.

Raises:
: KeyError: if the pipeline run doesn’t exist.

#### update_run_step(step_run_id: UUID, step_run_update: [StepRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunUpdate)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Updates a step run.

Args:
: step_run_id: The ID of the step to update.
  step_run_update: The update to be applied to the step.

Returns:
: The updated step run.

Raises:
: KeyError: if the step run doesn’t exist.

#### update_run_template(template_id: UUID, template_update: [RunTemplateUpdate](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateUpdate)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Updates a run template.

Args:
: template_id: The ID of the template to update.
  template_update: The update to apply.

Returns:
: The updated template.

Raises:
: KeyError: If the template does not exist.

#### update_schedule(schedule_id: UUID, schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Updates a schedule.

Args:
: schedule_id: The ID of the schedule to be updated.
  schedule_update: The update to be applied.

Returns:
: The updated schedule.

Raises:
: KeyError: if the schedule doesn’t exist.

#### update_secret(secret_id: UUID, secret_update: [SecretUpdate](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretUpdate)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Updates a secret.

Secret values that are specified as None in the update that are
present in the existing secret are removed from the existing secret.
Values that are present in both secrets are overwritten. All other
values in both the existing secret and the update are kept (merged).

If the update includes a change of name or scope, the scoping rules
enforced in the secrets store are used to validate the update:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret_id: The ID of the secret to be updated.
  secret_update: The update to be applied.

Returns:
: The updated secret.

Raises:
: KeyError: if the secret doesn’t exist.
  EntityExistsError: If a secret with the same name already exists in
  <br/>
  > the same scope.

#### update_server_settings(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate)) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Update the server settings.

Args:
: settings_update: The server settings update.

Returns:
: The updated server settings.

#### update_service(service_id: UUID, update: [ServiceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceUpdate)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Update a service.

Args:
: service_id: The ID of the service to update.
  update: The update to be applied to the service.

Returns:
: The updated service.

Raises:
: KeyError: if the service doesn’t exist.

#### update_service_account(service_account_name_or_id: str | UUID, service_account_update: [ServiceAccountUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountUpdate)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Updates an existing service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to update.
  <br/>
  service_account_update: The update to be applied to the service
  : account.

Returns:
: The updated service account.

Raises:
: EntityExistsError: If a user or service account with the given name
  : already exists.

#### update_service_connector(service_connector_id: UUID, update: [ServiceConnectorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorUpdate)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Updates an existing service connector.

The update model contains the fields to be updated. If a field value is
set to None in the model, the field is not updated, but there are
special rules concerning some fields:

* the configuration and secrets fields together represent a full

valid configuration update, not just a partial update. If either is
set (i.e. not None) in the update, their values are merged together and
will replace the existing configuration and secrets values.
\* the resource_id field value is also a full replacement value: if set
to None, the resource ID is removed from the service connector.
\* the expiration_seconds field value is also a full replacement value:
if set to None, the expiration is removed from the service connector.
\* the secret_id field value in the update is ignored, given that
secrets are managed internally by the ZenML store.
\* the labels field is also a full labels update: if set (i.e. not
None), all existing labels are removed and replaced by the new labels
in the update.

Args:
: service_connector_id: The ID of the service connector to update.
  update: The update to be applied to the service connector.

Returns:
: The updated service connector.

Raises:
: KeyError: If no service connector with the given ID exists.
  IllegalOperationError: If the service connector is referenced by
  <br/>
  > one or more stack components and the update would change the
  > connector type, resource type or resource ID.

#### update_stack(stack_id: UUID, stack_update: [StackUpdate](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackUpdate)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Update a stack.

Args:
: stack_id: The ID of the stack update.
  stack_update: The update request on the stack.

Returns:
: The updated stack.

Raises:
: KeyError: if the stack doesn’t exist.
  IllegalOperationError: if the stack is a default stack.

#### update_stack_component(component_id: UUID, component_update: [ComponentUpdate](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentUpdate)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Update an existing stack component.

Args:
: component_id: The ID of the stack component to update.
  component_update: The update to be applied to the stack component.

Returns:
: The updated stack component.

Raises:
: KeyError: if the stack component doesn’t exist.
  IllegalOperationError: if the stack component is a default stack
  <br/>
  > component.

#### update_tag(tag_name_or_id: str | UUID, tag_update_model: [TagUpdate](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagUpdate)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Update tag.

Args:
: tag_name_or_id: name or id of the tag to be updated.
  tag_update_model: Tag to use for the update.

Returns:
: An updated tag.

Raises:
: KeyError: If the tag is not found

#### update_trigger(trigger_id: UUID, trigger_update: [TriggerUpdate](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerUpdate)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Update a trigger.

Args:
: trigger_id: The ID of the trigger update.
  trigger_update: The update request on the trigger.

Returns:
: The updated trigger.

Raises:
: KeyError: If the trigger doesn’t exist.
  ValueError: If both a schedule and an event source are provided.

#### update_user(user_id: UUID, user_update: [UserUpdate](zenml.models.v2.core.md#zenml.models.v2.core.user.UserUpdate)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Updates an existing user.

Args:
: user_id: The id of the user to update.
  user_update: The update to be applied to the user.

Returns:
: The updated user.

Raises:
: IllegalOperationError: If the request tries to update the username
  : for the default user account.
  <br/>
  EntityExistsError: If the request tries to update the username to
  : a name that is already taken by another user or service account.

#### update_workspace(workspace_id: UUID, workspace_update: [WorkspaceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceUpdate)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Update an existing workspace.

Args:
: workspace_id: The ID of the workspace to be updated.
  workspace_update: The update to be applied to the workspace.

Returns:
: The updated workspace.

Raises:
: IllegalOperationError: if the workspace is the default workspace.
  KeyError: if the workspace does not exist.

#### verify_service_connector(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None, list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector instance has access to one or more resources.

Args:
: service_connector_id: The ID of the service connector to verify.
  resource_type: The type of resource to verify access to.
  resource_id: The ID of the resource to verify access to.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector and matching the supplied resource
  > type and ID are returned.

Returns:
: The list of resources that the service connector has access to,
  scoped to the supplied resource type and ID, if provided.

#### verify_service_connector_config(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest), list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector configuration has access to resources.

Args:
: service_connector: The service connector configuration to verify.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector is returned.

Returns:
: The list of resources that the service connector configuration has
  access to.

### *class* zenml.zen_stores.sql_zen_store.SqlZenStoreConfiguration(\*, type: [StoreType](zenml.md#zenml.enums.StoreType) = StoreType.SQL, url: str, secrets_store: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, backup_secrets_store: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, driver: [SQLDatabaseDriver](#zenml.zen_stores.sql_zen_store.SQLDatabaseDriver) | None = None, database: str | None = None, username: str | None = None, password: str | None = None, ssl_ca: str | None = None, ssl_cert: str | None = None, ssl_key: str | None = None, ssl_verify_server_cert: bool = False, pool_size: int = 20, max_overflow: int = 20, pool_pre_ping: bool = True, backup_strategy: [DatabaseBackupStrategy](zenml.md#zenml.enums.DatabaseBackupStrategy) = DatabaseBackupStrategy.IN_MEMORY, backup_directory: str = None, backup_database: str | None = None)

Bases: [`StoreConfiguration`](zenml.config.md#zenml.config.store_config.StoreConfiguration)

SQL ZenML store configuration.

Attributes:
: type: The type of the store.
  secrets_store: The configuration of the secrets store to use.
  <br/>
  > This defaults to a SQL secrets store that extends the SQL ZenML
  > store.
  <br/>
  backup_secrets_store: The configuration of a backup secrets store to
  : use in addition to the primary one as an intermediate step during
    the migration to a new secrets store.
  <br/>
  driver: The SQL database driver.
  database: database name. If not already present on the server, it will
  <br/>
  > be created automatically on first access.
  <br/>
  username: The database username.
  password: The database password.
  ssl_ca: certificate authority certificate. Required for SSL
  <br/>
  > enabled authentication if the CA certificate is not part of the
  > certificates shipped by the operating system.
  <br/>
  ssl_cert: client certificate. Required for SSL enabled
  : authentication if client certificates are used.
  <br/>
  ssl_key: client certificate private key. Required for SSL
  : enabled if client certificates are used.
  <br/>
  ssl_verify_server_cert: set to verify the identity of the server
  : against the provided server certificate.
  <br/>
  pool_size: The maximum number of connections to keep in the SQLAlchemy
  : pool.
  <br/>
  max_overflow: The maximum number of connections to allow in the
  : SQLAlchemy pool in addition to the pool_size.
  <br/>
  pool_pre_ping: Enable emitting a test statement on the SQL connection
  : at the start of each connection pool checkout, to test that the
    database connection is still viable.

#### backup_database *: str | None*

#### backup_directory *: str*

#### backup_secrets_store *: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None*

#### backup_strategy *: [DatabaseBackupStrategy](zenml.md#zenml.enums.DatabaseBackupStrategy)*

#### database *: str | None*

#### driver *: [SQLDatabaseDriver](#zenml.zen_stores.sql_zen_store.SQLDatabaseDriver) | None*

#### expand_certificates() → None

Expands the certificates in the verify_ssl field.

#### *static* get_local_url(path: str) → str

Get a local SQL url for a given local path.

Args:
: path: The path to the local sqlite file.

Returns:
: The local SQL url for the given path.

#### get_sqlalchemy_config(database: str | None = None) → Tuple[URL, Dict[str, Any], Dict[str, Any]]

Get the SQLAlchemy engine configuration for the SQL ZenML store.

Args:
: database: Custom database name to use. If not set, the database name
  : from the configuration will be used.

Returns:
: The URL and connection arguments for the SQLAlchemy engine.

Raises:
: NotImplementedError: If the SQL driver is not supported.

#### max_overflow *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'backup_database': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'backup_directory': FieldInfo(annotation=str, required=False, default_factory=<lambda>), 'backup_secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'backup_strategy': FieldInfo(annotation=DatabaseBackupStrategy, required=False, default=<DatabaseBackupStrategy.IN_MEMORY: 'in-memory'>), 'database': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'driver': FieldInfo(annotation=Union[SQLDatabaseDriver, NoneType], required=False, default=None), 'max_overflow': FieldInfo(annotation=int, required=False, default=20), 'password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'pool_pre_ping': FieldInfo(annotation=bool, required=False, default=True), 'pool_size': FieldInfo(annotation=int, required=False, default=20), 'secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'ssl_ca': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ssl_cert': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ssl_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ssl_verify_server_cert': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=StoreType, required=False, default=<StoreType.SQL: 'sql'>), 'url': FieldInfo(annotation=str, required=True), 'username': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: str | None*

#### pool_pre_ping *: bool*

#### pool_size *: int*

#### secrets_store *: Annotated[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None*

#### ssl_ca *: str | None*

#### ssl_cert *: str | None*

#### ssl_key *: str | None*

#### ssl_verify_server_cert *: bool*

#### *classmethod* supports_url_scheme(url: str) → bool

Check if a URL scheme is supported by this store.

Args:
: url: The URL to check.

Returns:
: True if the URL scheme is supported, False otherwise.

#### type *: [StoreType](zenml.md#zenml.enums.StoreType)*

#### username *: str | None*

#### *classmethod* validate_secrets_store(secrets_store: [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration) | None) → [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration)

Ensures that the secrets store is initialized with a default SQL secrets store.

Args:
: secrets_store: The secrets store config to be validated.

Returns:
: The validated secrets store config.

## zenml.zen_stores.template_utils module

Utilities for run templates.

### zenml.zen_stores.template_utils.generate_config_schema(deployment: [PipelineDeploymentSchema](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)) → Dict[str, Any]

Generate a run configuration schema for the deployment and stack.

Args:
: deployment: The deployment schema.

Returns:
: The generated schema dictionary.

### zenml.zen_stores.template_utils.generate_config_template(deployment: [PipelineDeploymentSchema](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)) → Dict[str, Any]

Generate a run configuration template for a deployment.

Args:
: deployment: The deployment.

Returns:
: The run configuration template.

### zenml.zen_stores.template_utils.validate_deployment_is_templatable(deployment: [PipelineDeploymentSchema](zenml.zen_stores.schemas.md#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)) → None

Validate that a deployment is templatable.

Args:
: deployment: The deployment to validate.

Raises:
: ValueError: If the deployment is not templatable.

## zenml.zen_stores.zen_store_interface module

ZenML Store interface.

### *class* zenml.zen_stores.zen_store_interface.ZenStoreInterface

Bases: `ABC`

ZenML store interface.

All ZenML stores must implement the methods in this interface.

The methods in this interface are organized in the following way:

> * they are grouped into categories based on the type of resource
>   that they operate on (e.g. stacks, stack components, etc.)
> * each category has a set of CRUD methods (create, read, update, delete)
>   that operate on the resources in that category. The order of the methods
>   in each category should be:
>   * create methods - store a new resource. These methods
>     should fill in generated fields (e.g. UUIDs, creation timestamps) in
>     the resource and return the updated resource.
>   * get methods - retrieve a single existing resource identified by a
>     unique key or identifier from the store. These methods should always
>     return a resource and raise an exception if the resource does not
>     exist.
>   * list methods - retrieve a list of resources from the store. These
>     methods should accept a set of filter parameters that can be used to
>     filter the list of resources retrieved from the store.
>   * update methods - update an existing resource in the store. These
>     methods should expect the updated resource to be correctly identified
>     by its unique key or identifier and raise an exception if the resource
>     does not exist.
>   * delete methods - delete an existing resource from the store. These
>     methods should expect the resource to be correctly identified by its
>     unique key or identifier. If the resource does not exist,
>     an exception should be raised.

Best practices for implementing and keeping this interface clean and easy to
maintain and extend:

> * keep methods organized by resource type and ordered by CRUD operation
> * for resources with multiple keys, don’t implement multiple get or list

> methods here if the same functionality can be achieved by a single get or
> list method. Instead, implement them in the BaseZenStore class and have
> them call the generic get or list method in this interface.
> \* keep the logic required to convert between ZenML domain Model classes
> and internal store representations outside the ZenML domain Model classes
> \* methods for resources that have two or more unique keys (e.g. a Workspace
> is uniquely identified by its name as well as its UUID) should reflect
> that in the method variants and/or method arguments:

> > * methods that take in a resource identifier as argument should accept

> > all variants of the identifier (e.g. workspace_name_or_uuid for methods
> > that get/list/update/delete Workspaces)
> > \* if a compound key is involved, separate get methods should be
> > implemented (e.g. get_pipeline to get a pipeline by ID and
> > get_pipeline_in_workspace to get a pipeline by its name and the ID of
> > the workspace it belongs to)
> * methods for resources that are scoped as children of other resources

> (e.g. a Stack is always owned by a Workspace) should reflect the
> key(s) of the parent resource in the provided methods and method
> arguments:

> > * create methods should take the parent resource UUID(s) as an argument

> > (e.g. create_stack takes in the workspace ID)
> > \* get methods should be provided to retrieve a resource by the compound
> > key that includes the parent resource key(s)
> > \* list methods should feature optional filter arguments that reflect
> > the parent resource key(s)

#### *abstract* backup_secrets(ignore_errors: bool = True, delete_secrets: bool = False) → None

Backs up all secrets to the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the backup
  : process and attempt to backup all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully backed up from the primary secrets store. Setting
    this flag effectively moves all secrets from the primary secrets
    store to the backup secrets store.

Raises:
: BackupSecretsStoreNotConfiguredError: if no backup secrets store is
  : configured.

#### *abstract* create_action(action: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Create an action.

Args:
: action: The action to create.

Returns:
: The created action.

#### *abstract* create_api_key(service_account_id: UUID, api_key: [APIKeyRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Create a new API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : create the API key.
  <br/>
  api_key: The API key to create.

Returns:
: The created API key.

Raises:
: KeyError: If the service account doesn’t exist.
  EntityExistsError: If an API key with the same name is already
  <br/>
  > configured for the same service account.

#### *abstract* create_artifact(artifact: [ArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactRequest)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Creates a new artifact.

Args:
: artifact: The artifact to create.

Returns:
: The newly created artifact.

Raises:
: EntityExistsError: If an artifact with the same name already exists.

#### *abstract* create_artifact_version(artifact_version: [ArtifactVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionRequest)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Creates an artifact version.

Args:
: artifact_version: The artifact version to create.

Returns:
: The created artifact version.

#### *abstract* create_build(build: [PipelineBuildRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildRequest)) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Creates a new build in a workspace.

Args:
: build: The build to create.

Returns:
: The newly created build.

Raises:
: KeyError: If the workspace does not exist.
  EntityExistsError: If an identical build already exists.

#### *abstract* create_code_repository(code_repository: [CodeRepositoryRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryRequest)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Creates a new code repository.

Args:
: code_repository: Code repository to be created.

Returns:
: The newly created code repository.

Raises:
: EntityExistsError: If a code repository with the given name already
  : exists.

#### *abstract* create_deployment(deployment: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest)) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Creates a new deployment in a workspace.

Args:
: deployment: The deployment to create.

Returns:
: The newly created deployment.

Raises:
: KeyError: If the workspace does not exist.
  EntityExistsError: If an identical deployment already exists.

#### *abstract* create_event_source(event_source: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Create an event_source.

Args:
: event_source: The event_source to create.

Returns:
: The created event_source.

#### *abstract* create_flavor(flavor: [FlavorRequest](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorRequest)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Creates a new stack component flavor.

Args:
: flavor: The stack component flavor to create.

Returns:
: The newly created flavor.

Raises:
: EntityExistsError: If a flavor with the same name and type
  : is already owned by this user in this workspace.

#### *abstract* create_model(model: [ModelRequest](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelRequest)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Creates a new model.

Args:
: model: the Model to be created.

Returns:
: The newly created model.

Raises:
: EntityExistsError: If a model with the given name already exists.

#### *abstract* create_model_version(model_version: [ModelVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionRequest)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Creates a new model version.

Args:
: model_version: the Model Version to be created.

Returns:
: The newly created model version.

Raises:
: ValueError: If number is not None during model version creation.
  EntityExistsError: If a model version with the given name already
  <br/>
  > exists.

#### *abstract* create_model_version_artifact_link(model_version_artifact_link: [ModelVersionArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest)) → [ModelVersionArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse)

Creates a new model version link.

Args:
: model_version_artifact_link: the Model Version to Artifact Link
  : to be created.

Returns:
: The newly created model version to artifact link.

Raises:
: EntityExistsError: If a link with the given name already exists.

#### *abstract* create_model_version_pipeline_run_link(model_version_pipeline_run_link: [ModelVersionPipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest)) → [ModelVersionPipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse)

Creates a new model version to pipeline run link.

Args:
: model_version_pipeline_run_link: the Model Version to Pipeline Run
  : Link to be created.

Returns:
: - If Model Version to Pipeline Run Link already exists - returns
    : the existing link.
  - Otherwise, returns the newly created model version to pipeline
    : run link.

#### *abstract* create_pipeline(pipeline: [PipelineRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineRequest)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Creates a new pipeline in a workspace.

Args:
: pipeline: The pipeline to create.

Returns:
: The newly created pipeline.

Raises:
: KeyError: if the workspace does not exist.
  EntityExistsError: If an identical pipeline already exists.

#### *abstract* create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Creates a pipeline run.

Args:
: pipeline_run: The pipeline run to create.

Returns:
: The created pipeline run.

Raises:
: EntityExistsError: If an identical pipeline run already exists.
  KeyError: If the pipeline does not exist.

#### *abstract* create_run_metadata(run_metadata: [RunMetadataRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataRequest)) → List[[RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)]

Creates run metadata.

Args:
: run_metadata: The run metadata to create.

Returns:
: The created run metadata.

#### *abstract* create_run_step(step_run: [StepRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunRequest)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Creates a step run.

Args:
: step_run: The step run to create.

Returns:
: The created step run.

Raises:
: EntityExistsError: if the step run already exists.
  KeyError: if the pipeline run doesn’t exist.

#### *abstract* create_run_template(template: [RunTemplateRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateRequest)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Create a new run template.

Args:
: template: The template to create.

Returns:
: The newly created template.

Raises:
: EntityExistsError: If a template with the same name already exists.

#### *abstract* create_schedule(schedule: [ScheduleRequest](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleRequest)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Creates a new schedule.

Args:
: schedule: The schedule to create.

Returns:
: The newly created schedule.

#### *abstract* create_secret(secret: [SecretRequest](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretRequest)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Creates a new secret.

The new secret is also validated against the scoping rules enforced in
the secrets store:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret: The secret to create.

Returns:
: The newly created secret.

Raises:
: KeyError: if the user or workspace does not exist.
  EntityExistsError: If a secret with the same name already exists in
  <br/>
  > the same scope.

#### *abstract* create_service(service: [ServiceRequest](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceRequest)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Create a new service.

Args:
: service: The service to create.

Returns:
: The newly created service.

Raises:
: EntityExistsError: If a service with the same name already exists.

#### *abstract* create_service_account(service_account: [ServiceAccountRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountRequest)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Creates a new service account.

Args:
: service_account: Service account to be created.

Returns:
: The newly created service account.

Raises:
: EntityExistsError: If a user or service account with the given name
  : already exists.

#### *abstract* create_service_connector(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Creates a new service connector.

Args:
: service_connector: Service connector to be created.

Returns:
: The newly created service connector.

Raises:
: EntityExistsError: If a service connector with the given name
  : is already owned by this user in this workspace.

#### *abstract* create_stack(stack: [StackRequest](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackRequest)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Create a new stack.

Args:
: stack: The stack to create.

Returns:
: The created stack.

Raises:
: EntityExistsError: If a service connector with the same name
  : already exists.
  <br/>
  StackComponentExistsError: If a stack component with the same name
  : already exists.
  <br/>
  StackExistsError: If a stack with the same name already exists.

#### *abstract* create_stack_component(component: [ComponentRequest](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentRequest)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Create a stack component.

Args:
: component: The stack component to create.

Returns:
: The created stack component.

Raises:
: StackComponentExistsError: If a stack component with the same name
  : and type is already owned by this user in this workspace.

#### *abstract* create_tag(tag: [TagRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagRequest)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Creates a new tag.

Args:
: tag: the tag to be created.

Returns:
: The newly created tag.

Raises:
: EntityExistsError: If a tag with the given name already exists.

#### *abstract* create_trigger(trigger: [TriggerRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerRequest)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Create an trigger.

Args:
: trigger: The trigger to create.

Returns:
: The created trigger.

#### *abstract* create_user(user: [UserRequest](zenml.models.v2.core.md#zenml.models.v2.core.user.UserRequest)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Creates a new user.

Args:
: user: User to be created.

Returns:
: The newly created user.

Raises:
: EntityExistsError: If a user with the given name already exists.

#### *abstract* create_workspace(workspace: [WorkspaceRequest](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceRequest)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Creates a new workspace.

Args:
: workspace: The workspace to create.

Returns:
: The newly created workspace.

Raises:
: EntityExistsError: If a workspace with the given name already exists.

#### *abstract* delete_action(action_id: UUID) → None

Delete an action.

Args:
: action_id: The ID of the action to delete.

Raises:
: KeyError: If the action doesn’t exist.

#### *abstract* delete_all_model_version_artifact_links(model_version_id: UUID, only_links: bool = True) → None

Deletes all model version to artifact links.

Args:
: model_version_id: ID of the model version containing the link.
  only_links: Flag deciding whether to delete only links or all.

#### *abstract* delete_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID) → None

Delete an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : delete the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to delete.

Raises:
: KeyError: if an API key with the given name or ID is not configured
  : for the given service account.

#### *abstract* delete_artifact(artifact_id: UUID) → None

Deletes an artifact.

Args:
: artifact_id: The ID of the artifact to delete.

Raises:
: KeyError: if the artifact doesn’t exist.

#### *abstract* delete_artifact_version(artifact_version_id: UUID) → None

Deletes an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to delete.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### *abstract* delete_authorized_device(device_id: UUID) → None

Deletes an OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to delete.

Raises:
: KeyError: If no device with the given ID exists.

#### *abstract* delete_build(build_id: UUID) → None

Deletes a build.

Args:
: build_id: The ID of the build to delete.

Raises:
: KeyError: if the build doesn’t exist.

#### *abstract* delete_code_repository(code_repository_id: UUID) → None

Deletes a code repository.

Args:
: code_repository_id: The ID of the code repository to delete.

Raises:
: KeyError: If no code repository with the given ID exists.

#### *abstract* delete_deployment(deployment_id: UUID) → None

Deletes a deployment.

Args:
: deployment_id: The ID of the deployment to delete.

Raises:
: KeyError: If the deployment doesn’t exist.

#### *abstract* delete_event_source(event_source_id: UUID) → None

Delete an event_source.

Args:
: event_source_id: The ID of the event_source to delete.

Raises:
: KeyError: if the event_source doesn’t exist.

#### *abstract* delete_flavor(flavor_id: UUID) → None

Delete a stack component flavor.

Args:
: flavor_id: The ID of the stack component flavor to delete.

Raises:
: KeyError: if the stack component flavor doesn’t exist.

#### *abstract* delete_model(model_name_or_id: str | UUID) → None

Deletes a model.

Args:
: model_name_or_id: name or id of the model to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* delete_model_version(model_version_id: UUID) → None

Deletes a model version.

Args:
: model_version_id: id of the model version to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* delete_model_version_artifact_link(model_version_id: UUID, model_version_artifact_link_name_or_id: str | UUID) → None

Deletes a model version to artifact link.

Args:
: model_version_id: ID of the model version containing the link.
  model_version_artifact_link_name_or_id: name or ID of the model
  <br/>
  > version to artifact link to be deleted.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* delete_model_version_pipeline_run_link(model_version_id: UUID, model_version_pipeline_run_link_name_or_id: str | UUID) → None

Deletes a model version to pipeline run link.

Args:
: model_version_id: ID of the model version containing the link.
  model_version_pipeline_run_link_name_or_id: name or ID of the model
  <br/>
  > version to pipeline run link to be deleted.

Raises:
: KeyError: specified ID not found.

#### *abstract* delete_pipeline(pipeline_id: UUID) → None

Deletes a pipeline.

Args:
: pipeline_id: The ID of the pipeline to delete.

Raises:
: KeyError: if the pipeline doesn’t exist.

#### *abstract* delete_run(run_id: UUID) → None

Deletes a pipeline run.

Args:
: run_id: The ID of the pipeline run to delete.

Raises:
: KeyError: if the pipeline run doesn’t exist.

#### *abstract* delete_run_template(template_id: UUID) → None

Delete a run template.

Args:
: template_id: The ID of the template to delete.

Raises:
: KeyError: If the template does not exist.

#### *abstract* delete_schedule(schedule_id: UUID) → None

Deletes a schedule.

Args:
: schedule_id: The ID of the schedule to delete.

Raises:
: KeyError: if the schedule doesn’t exist.

#### *abstract* delete_secret(secret_id: UUID) → None

Deletes a secret.

Args:
: secret_id: The ID of the secret to delete.

Raises:
: KeyError: if the secret doesn’t exist.

#### *abstract* delete_service(service_id: UUID) → None

Delete a service.

Args:
: service_id: The ID of the service to delete.

Raises:
: KeyError: if the service doesn’t exist.

#### *abstract* delete_service_account(service_account_name_or_id: str | UUID) → None

Delete a service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to delete.

Raises:
: IllegalOperationError: if the service account has already been used
  : to create other resources.

#### *abstract* delete_service_connector(service_connector_id: UUID) → None

Deletes a service connector.

Args:
: service_connector_id: The ID of the service connector to delete.

Raises:
: KeyError: If no service connector with the given ID exists.

#### *abstract* delete_stack(stack_id: UUID) → None

Delete a stack.

Args:
: stack_id: The ID of the stack to delete.

Raises:
: KeyError: if the stack doesn’t exist.

#### *abstract* delete_stack_component(component_id: UUID) → None

Delete a stack component.

Args:
: component_id: The ID of the stack component to delete.

Raises:
: KeyError: if the stack component doesn’t exist.
  ValueError: if the stack component is part of one or more stacks.

#### *abstract* delete_tag(tag_name_or_id: str | UUID) → None

Deletes a tag.

Args:
: tag_name_or_id: name or id of the tag to delete.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* delete_trigger(trigger_id: UUID) → None

Delete an trigger.

Args:
: trigger_id: The ID of the trigger to delete.

Raises:
: KeyError: if the trigger doesn’t exist.

#### *abstract* delete_trigger_execution(trigger_execution_id: UUID) → None

Delete a trigger execution.

Args:
: trigger_execution_id: The ID of the trigger execution to delete.

Raises:
: KeyError: If the trigger execution doesn’t exist.

#### *abstract* delete_user(user_name_or_id: str | UUID) → None

Deletes a user.

Args:
: user_name_or_id: The name or ID of the user to delete.

Raises:
: KeyError: If no user with the given ID exists.

#### *abstract* delete_workspace(workspace_name_or_id: str | UUID) → None

Deletes a workspace.

Args:
: workspace_name_or_id: Name or ID of the workspace to delete.

Raises:
: KeyError: If no workspace with the given name exists.

#### *abstract* get_action(action_id: UUID, hydrate: bool = True) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Get an action by ID.

Args:
: action_id: The ID of the action to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The action.

Raises:
: KeyError: If the action doesn’t exist.

#### *abstract* get_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, hydrate: bool = True) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Get an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to fetch
  : the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The API key with the given ID.

Raises:
: KeyError: if an API key with the given name or ID is not configured
  : for the given service account.

#### *abstract* get_artifact(artifact_id: UUID, hydrate: bool = True) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Gets an artifact.

Args:
: artifact_id: The ID of the artifact to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact.

Raises:
: KeyError: if the artifact doesn’t exist.

#### *abstract* get_artifact_version(artifact_version_id: UUID, hydrate: bool = True) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Gets an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The artifact version.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### *abstract* get_artifact_visualization(artifact_visualization_id: UUID, hydrate: bool = True) → [ArtifactVisualizationResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Gets an artifact visualization.

Args:
: artifact_visualization_id: The ID of the artifact visualization
  : to get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The artifact visualization.

Raises:
: KeyError: if the artifact visualization doesn’t exist.

#### *abstract* get_authorized_device(device_id: UUID, hydrate: bool = True) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Gets a specific OAuth 2.0 authorized device.

Args:
: device_id: The ID of the device to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested device, if it was found.

Raises:
: KeyError: If no device with the given ID exists.

#### *abstract* get_build(build_id: UUID, hydrate: bool = True) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Get a build with a given ID.

Args:
: build_id: ID of the build.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The build.

Raises:
: KeyError: If the build does not exist.

#### *abstract* get_code_reference(code_reference_id: UUID, hydrate: bool = True) → [CodeReferenceResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Gets a specific code reference.

Args:
: code_reference_id: The ID of the code reference to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested code reference, if it was found.

Raises:
: KeyError: If no code reference with the given ID exists.

#### *abstract* get_code_repository(code_repository_id: UUID, hydrate: bool = True) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Gets a specific code repository.

Args:
: code_repository_id: The ID of the code repository to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested code repository, if it was found.

Raises:
: KeyError: If no code repository with the given ID exists.

#### *abstract* get_deployment(deployment_id: UUID, hydrate: bool = True) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Get a deployment with a given ID.

Args:
: deployment_id: ID of the deployment.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The deployment.

Raises:
: KeyError: If the deployment does not exist.

#### *abstract* get_deployment_id() → UUID

Get the ID of the deployment.

Returns:
: The ID of the deployment.

#### *abstract* get_event_source(event_source_id: UUID, hydrate: bool = True) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Get an event_source by ID.

Args:
: event_source_id: The ID of the event_source to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The event_source.

Raises:
: KeyError: if the stack event_source doesn’t exist.

#### *abstract* get_flavor(flavor_id: UUID, hydrate: bool = True) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Get a stack component flavor by ID.

Args:
: flavor_id: The ID of the flavor to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component flavor.

Raises:
: KeyError: if the stack component flavor doesn’t exist.

#### *abstract* get_logs(logs_id: UUID, hydrate: bool = True) → [LogsResponse](zenml.models.v2.core.md#zenml.models.v2.core.logs.LogsResponse)

Get logs by its unique ID.

Args:
: logs_id: The ID of the logs to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The logs with the given ID.

Raises:
: KeyError: if the logs doesn’t exist.

#### *abstract* get_model(model_name_or_id: str | UUID, hydrate: bool = True) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Get an existing model.

Args:
: model_name_or_id: name or id of the model to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The model of interest.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* get_model_version(model_version_id: UUID, hydrate: bool = True) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get an existing model version.

Args:
: model_version_id: name, id, stage or number of the model version to
  : be retrieved. If skipped - latest is retrieved.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The model version of interest.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* get_or_create_run(pipeline_run: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → Tuple[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse), bool]

Gets or creates a pipeline run.

If a run with the same ID or name already exists, it is returned.
Otherwise, a new run is created.

Args:
: pipeline_run: The pipeline run to get or create.

Returns:
: The pipeline run, and a boolean indicating whether the run was
  created or not.

#### *abstract* get_pipeline(pipeline_id: UUID, hydrate: bool = True) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Get a pipeline with a given ID.

Args:
: pipeline_id: ID of the pipeline.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline.

Raises:
: KeyError: if the pipeline does not exist.

#### *abstract* get_run(run_name_or_id: str | UUID, hydrate: bool = True) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Gets a pipeline run.

Args:
: run_name_or_id: The name or ID of the pipeline run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The pipeline run.

Raises:
: KeyError: if the pipeline run doesn’t exist.

#### *abstract* get_run_metadata(run_metadata_id: UUID, hydrate: bool = True) → [RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Get run metadata by its unique ID.

Args:
: run_metadata_id: The ID of the run metadata to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The run metadata with the given ID.

Raises:
: KeyError: if the run metadata doesn’t exist.

#### *abstract* get_run_step(step_run_id: UUID, hydrate: bool = True) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Get a step run by ID.

Args:
: step_run_id: The ID of the step run to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The step run.

Raises:
: KeyError: if the step run doesn’t exist.

#### *abstract* get_run_template(template_id: UUID, hydrate: bool = True) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Get a run template with a given ID.

Args:
: template_id: ID of the template.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The template.

Raises:
: KeyError: If the template does not exist.

#### *abstract* get_schedule(schedule_id: UUID, hydrate: bool = True) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Get a schedule with a given ID.

Args:
: schedule_id: ID of the schedule.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The schedule.

Raises:
: KeyError: if the schedule does not exist.

#### *abstract* get_secret(secret_id: UUID, hydrate: bool = True) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Get a secret with a given name.

Args:
: secret_id: ID of the secret.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The secret.

Raises:
: KeyError: if the secret does not exist.

#### *abstract* get_server_settings(hydrate: bool = True) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Get the server settings.

Args:
: hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The server settings.

#### *abstract* get_service(service_id: UUID, hydrate: bool = True) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Get a service by ID.

Args:
: service_id: The ID of the service to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The service.

Raises:
: KeyError: if the service doesn’t exist.

#### *abstract* get_service_account(service_account_name_or_id: str | UUID, hydrate: bool = True) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Gets a specific service account.

Args:
: service_account_name_or_id: The name or ID of the service account to
  : get.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The requested service account, if it was found.

Raises:
: KeyError: If no service account with the given name or ID exists.

#### *abstract* get_service_connector(service_connector_id: UUID, hydrate: bool = True) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Gets a specific service connector.

Args:
: service_connector_id: The ID of the service connector to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested service connector, if it was found.

Raises:
: KeyError: If no service connector with the given ID exists.

#### *abstract* get_service_connector_client(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Get a service connector client for a service connector and given resource.

Args:
: service_connector_id: The ID of the base service connector to use.
  resource_type: The type of resource to get a client for.
  resource_id: The ID of the resource to get a client for.

Returns:
: A service connector client that can be used to access the given
  resource.

Raises:
: KeyError: If no service connector with the given name exists.
  NotImplementError: If the service connector cannot be instantiated
  <br/>
  > on the store e.g. due to missing package dependencies.

#### *abstract* get_service_connector_type(connector_type: str) → [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)

Returns the requested service connector type.

Args:
: connector_type: the service connector type identifier.

Returns:
: The requested service connector type.

Raises:
: KeyError: If no service connector type with the given ID exists.

#### *abstract* get_stack(stack_id: UUID, hydrate: bool = True) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Get a stack by its unique ID.

Args:
: stack_id: The ID of the stack to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack with the given ID.

Raises:
: KeyError: if the stack doesn’t exist.

#### *abstract* get_stack_component(component_id: UUID, hydrate: bool = True) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Get a stack component by ID.

Args:
: component_id: The ID of the stack component to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The stack component.

Raises:
: KeyError: if the stack component doesn’t exist.

#### *abstract* get_stack_deployment_config(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None) → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the cloud provider console URL and configuration needed to deploy the ZenML stack.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.

Returns:
: The cloud provider console URL and configuration needed to deploy
  the ZenML stack to the specified cloud provider.

#### *abstract* get_stack_deployment_info(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)) → [StackDeploymentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentInfo)

Get information about a stack deployment provider.

Args:
: provider: The stack deployment provider.

Returns:
: Information about the stack deployment provider.

#### *abstract* get_stack_deployment_stack(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), stack_name: str, location: str | None = None, date_start: datetime | None = None) → [DeployedStack](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.DeployedStack) | None

Return a matching ZenML stack that was deployed and registered.

Args:
: provider: The stack deployment provider.
  stack_name: The name of the stack.
  location: The location where the stack should be deployed.
  date_start: The date when the deployment started.

Returns:
: The ZenML stack that was deployed and registered or None if the
  stack was not found.

#### *abstract* get_store_info() → [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)

Get information about the store.

Returns:
: Information about the store.

#### *abstract* get_tag(tag_name_or_id: str | UUID, hydrate: bool = True) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Get an existing tag.

Args:
: tag_name_or_id: name or id of the tag to be retrieved.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The tag of interest.

Raises:
: KeyError: specified ID or name not found.

#### *abstract* get_trigger(trigger_id: UUID, hydrate: bool = True) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Get an trigger by ID.

Args:
: trigger_id: The ID of the trigger to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger.

Raises:
: KeyError: if the stack trigger doesn’t exist.

#### *abstract* get_trigger_execution(trigger_execution_id: UUID, hydrate: bool = True) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Get an trigger execution by ID.

Args:
: trigger_execution_id: The ID of the trigger execution to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The trigger execution.

Raises:
: KeyError: If the trigger execution doesn’t exist.

#### *abstract* get_user(user_name_or_id: str | UUID | None = None, include_private: bool = False, hydrate: bool = True) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Gets a specific user, when no id is specified the active user is returned.

Args:
: user_name_or_id: The name or ID of the user to get.
  include_private: Whether to include private user information.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested user, if it was found.

Raises:
: KeyError: If no user with the given name or ID exists.

#### *abstract* get_workspace(workspace_name_or_id: UUID | str, hydrate: bool = True) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Get an existing workspace by name or ID.

Args:
: workspace_name_or_id: Name or ID of the workspace to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: The requested workspace.

Raises:
: KeyError: If there is no such workspace.

#### *abstract* list_actions(action_filter_model: [ActionFilter](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ActionResponse](zenml.models.md#zenml.models.ActionResponse)]

List all actions matching the given filter criteria.

Args:
: action_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all actions matching the filter criteria.

#### *abstract* list_api_keys(service_account_id: UUID, filter_model: [APIKeyFilter](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[APIKeyResponse](zenml.models.md#zenml.models.APIKeyResponse)]

List all API keys for a service account matching the given filter criteria.

Args:
: service_account_id: The ID of the service account for which to list
  : the API keys.
  <br/>
  filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all API keys matching the filter criteria.

#### *abstract* list_artifact_versions(artifact_version_filter_model: [ArtifactVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]

List all artifact versions matching the given filter criteria.

Args:
: artifact_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifact versions matching the filter criteria.

#### *abstract* list_artifacts(filter_model: [ArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ArtifactResponse](zenml.models.md#zenml.models.ArtifactResponse)]

List all artifacts matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all artifacts matching the filter criteria.

#### *abstract* list_authorized_devices(filter_model: [OAuthDeviceFilter](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[OAuthDeviceResponse](zenml.models.md#zenml.models.OAuthDeviceResponse)]

List all OAuth 2.0 authorized devices for a user.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all matching OAuth 2.0 authorized devices.

#### *abstract* list_builds(build_filter_model: [PipelineBuildFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse)]

List all builds matching the given filter criteria.

Args:
: build_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all builds matching the filter criteria.

#### *abstract* list_code_repositories(filter_model: [CodeRepositoryFilter](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[CodeRepositoryResponse](zenml.models.md#zenml.models.CodeRepositoryResponse)]

List all code repositories.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all code repositories.

#### *abstract* list_deployments(deployment_filter_model: [PipelineDeploymentFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)]

List all deployments matching the given filter criteria.

Args:
: deployment_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all deployments matching the filter criteria.

#### *abstract* list_event_sources(event_source_filter_model: [EventSourceFilter](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[EventSourceResponse](zenml.models.md#zenml.models.EventSourceResponse)]

List all event_sources matching the given filter criteria.

Args:
: event_source_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all event_sources matching the filter criteria.

#### *abstract* list_flavors(flavor_filter_model: [FlavorFilter](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[FlavorResponse](zenml.models.md#zenml.models.FlavorResponse)]

List all stack component flavors matching the given filter criteria.

Args:
: flavor_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: List of all the stack component flavors matching the given criteria.

#### *abstract* list_model_version_artifact_links(model_version_artifact_link_filter_model: [ModelVersionArtifactFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionArtifactResponse](zenml.models.md#zenml.models.ModelVersionArtifactResponse)]

Get all model version to artifact links by filter.

Args:
: model_version_artifact_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to artifact links.

#### *abstract* list_model_version_pipeline_run_links(model_version_pipeline_run_link_filter_model: [ModelVersionPipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionPipelineRunResponse](zenml.models.md#zenml.models.ModelVersionPipelineRunResponse)]

Get all model version to pipeline run links by filter.

Args:
: model_version_pipeline_run_link_filter_model: All filter parameters
  : including pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model version to pipeline run links.

#### *abstract* list_model_versions(model_version_filter_model: [ModelVersionFilter](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionFilter), model_name_or_id: str | UUID | None = None, hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelVersionResponse](zenml.models.md#zenml.models.ModelVersionResponse)]

Get all model versions by filter.

Args:
: model_name_or_id: name or id of the model containing the model
  : versions.
  <br/>
  model_version_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all model versions.

#### *abstract* list_models(model_filter_model: [ModelFilter](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ModelResponse](zenml.models.md#zenml.models.ModelResponse)]

Get all models by filter.

Args:
: model_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all models.

#### *abstract* list_pipelines(pipeline_filter_model: [PipelineFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineResponse](zenml.models.md#zenml.models.PipelineResponse)]

List all pipelines matching the given filter criteria.

Args:
: pipeline_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipelines matching the filter criteria.

#### *abstract* list_run_metadata(run_metadata_filter_model: [RunMetadataFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]

List run metadata.

Args:
: run_metadata_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: The run metadata.

#### *abstract* list_run_steps(step_run_filter_model: [StepRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)]

List all step runs matching the given filter criteria.

Args:
: step_run_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all step runs matching the filter criteria.

#### *abstract* list_run_templates(template_filter_model: [RunTemplateFilter](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[RunTemplateResponse](zenml.models.md#zenml.models.RunTemplateResponse)]

List all run templates matching the given filter criteria.

Args:
: template_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all templates matching the filter criteria.

#### *abstract* list_runs(runs_filter_model: [PipelineRunFilter](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]

List all pipeline runs matching the given filter criteria.

Args:
: runs_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all pipeline runs matching the filter criteria.

#### *abstract* list_schedules(schedule_filter_model: [ScheduleFilter](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse)]

List all schedules in the workspace.

Args:
: schedule_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of schedules.

#### *abstract* list_secrets(secret_filter_model: [SecretFilter](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[SecretResponse](zenml.models.md#zenml.models.SecretResponse)]

List all secrets matching the given filter criteria.

Note that returned secrets do not include any secret values. To fetch
the secret values, use get_secret.

Args:
: secret_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all secrets matching the filter criteria, with pagination
  information and sorted according to the filter criteria. The
  returned secrets do not include any secret values, only metadata. To
  fetch the secret values, use get_secret individually with each
  secret.

#### *abstract* list_service_accounts(filter_model: [ServiceAccountFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceAccountResponse](zenml.models.md#zenml.models.ServiceAccountResponse)]

List all service accounts.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of filtered service accounts.

#### *abstract* list_service_connector_resources(workspace_name_or_id: str | UUID, connector_type: str | None = None, resource_type: str | None = None, resource_id: str | None = None) → List[[ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)]

List resources that can be accessed by service connectors.

Args:
: workspace_name_or_id: The name or ID of the workspace to scope to.
  connector_type: The type of service connector to scope to.
  resource_type: The type of resource to scope to.
  resource_id: The ID of the resource to scope to.

Returns:
: The matching list of resources that available service
  connectors have access to.

#### *abstract* list_service_connector_types(connector_type: str | None = None, resource_type: str | None = None, auth_method: str | None = None) → List[[ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)]

Get a list of service connector types.

Args:
: connector_type: Filter by connector type.
  resource_type: Filter by resource type.
  auth_method: Filter by authentication method.

Returns:
: List of service connector types.

#### *abstract* list_service_connectors(filter_model: [ServiceConnectorFilter](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse)]

List all service connectors.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A page of all service connectors.

#### *abstract* list_services(filter_model: [ServiceFilter](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)]

List all services matching the given filter criteria.

Args:
: filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all services matching the filter criteria.

#### *abstract* list_stack_components(component_filter_model: [ComponentFilter](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]

List all stack components matching the given filter criteria.

Args:
: component_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stack components matching the filter criteria.

#### *abstract* list_stacks(stack_filter_model: [StackFilter](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[StackResponse](zenml.models.md#zenml.models.StackResponse)]

List all stacks matching the given filter criteria.

Args:
: stack_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all stacks matching the filter criteria.

#### *abstract* list_tags(tag_filter_model: [TagFilter](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TagResponse](zenml.models.md#zenml.models.TagResponse)]

Get all tags by filter.

Args:
: tag_filter_model: All filter parameters including pagination params.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: A page of all tags.

#### *abstract* list_trigger_executions(trigger_execution_filter_model: [TriggerExecutionFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)]

List all trigger executions matching the given filter criteria.

Args:
: trigger_execution_filter_model: All filter parameters including
  : pagination params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all trigger executions matching the filter criteria.

#### *abstract* list_triggers(trigger_filter_model: [TriggerFilter](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)]

List all triggers matching the given filter criteria.

Args:
: trigger_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all triggers matching the filter criteria.

#### *abstract* list_users(user_filter_model: [UserFilter](zenml.models.v2.core.md#zenml.models.v2.core.user.UserFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[UserResponse](zenml.models.md#zenml.models.UserResponse)]

List all users.

Args:
: user_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all users.

#### *abstract* list_workspaces(workspace_filter_model: [WorkspaceFilter](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceFilter), hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)]

List all workspace matching the given filter criteria.

Args:
: workspace_filter_model: All filter parameters including pagination
  : params.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: A list of all workspace matching the filter criteria.

#### *abstract* prune_artifact_versions(only_versions: bool = True) → None

Prunes unused artifact versions and their artifacts.

Args:
: only_versions: Only delete artifact versions, keeping artifacts

#### *abstract* restore_secrets(ignore_errors: bool = False, delete_secrets: bool = False) → None

Restore all secrets from the configured backup secrets store.

Args:
: ignore_errors: Whether to ignore individual errors during the
  : restore process and attempt to restore all secrets.
  <br/>
  delete_secrets: Whether to delete the secrets that have been
  : successfully restored from the backup secrets store. Setting
    this flag effectively moves all secrets from the backup secrets
    store to the primary secrets store.

Raises:
: BackupSecretsStoreNotConfiguredError: if no backup secrets store is
  : configured.

#### *abstract* rotate_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, rotate_request: [APIKeyRotateRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRotateRequest)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Rotate an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to
  : rotate the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to rotate.
  rotate_request: The rotate request on the API key.

Returns:
: The updated API key.

Raises:
: KeyError: if an API key with the given name or ID is not configured
  : for the given service account.

#### *abstract* run_template(template_id: UUID, run_configuration: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) | None = None) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Run a template.

Args:
: template_id: The ID of the template to run.
  run_configuration: Configuration for the run.

Returns:
: Model of the pipeline run.

#### *abstract* update_action(action_id: UUID, action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Update an existing action.

Args:
: action_id: The ID of the action to update.
  action_update: The update to be applied to the action.

Returns:
: The updated action.

Raises:
: KeyError: If the action doesn’t exist.

#### *abstract* update_api_key(service_account_id: UUID, api_key_name_or_id: str | UUID, api_key_update: [APIKeyUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyUpdate)) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Update an API key for a service account.

Args:
: service_account_id: The ID of the service account for which to update
  : the API key.
  <br/>
  api_key_name_or_id: The name or ID of the API key to update.
  api_key_update: The update request on the API key.

Returns:
: The updated API key.

Raises:
: KeyError: if an API key with the given name or ID is not configured
  : for the given service account.
  <br/>
  EntityExistsError: if the API key update would result in a name
  : conflict with an existing API key for the same service account.

#### *abstract* update_artifact(artifact_id: UUID, artifact_update: [ArtifactUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactUpdate)) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Updates an artifact.

Args:
: artifact_id: The ID of the artifact to update.
  artifact_update: The update to be applied to the artifact.

Returns:
: The updated artifact.

Raises:
: KeyError: if the artifact doesn’t exist.

#### *abstract* update_artifact_version(artifact_version_id: UUID, artifact_version_update: [ArtifactVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionUpdate)) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Updates an artifact version.

Args:
: artifact_version_id: The ID of the artifact version to update.
  artifact_version_update: The update to be applied to the artifact
  <br/>
  > version.

Returns:
: The updated artifact version.

Raises:
: KeyError: if the artifact version doesn’t exist.

#### *abstract* update_authorized_device(device_id: UUID, update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Updates an existing OAuth 2.0 authorized device for internal use.

Args:
: device_id: The ID of the device to update.
  update: The update to be applied to the device.

Returns:
: The updated OAuth 2.0 authorized device.

Raises:
: KeyError: If no device with the given ID exists.

#### *abstract* update_code_repository(code_repository_id: UUID, update: [CodeRepositoryUpdate](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryUpdate)) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Updates an existing code repository.

Args:
: code_repository_id: The ID of the code repository to update.
  update: The update to be applied to the code repository.

Returns:
: The updated code repository.

Raises:
: KeyError: If no code repository with the given name exists.

#### *abstract* update_event_source(event_source_id: UUID, event_source_update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Update an existing event_source.

Args:
: event_source_id: The ID of the event_source to update.
  event_source_update: The update to be applied to the event_source.

Returns:
: The updated event_source.

Raises:
: KeyError: if the event_source doesn’t exist.

#### *abstract* update_flavor(flavor_id: UUID, flavor_update: [FlavorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorUpdate)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Updates an existing user.

Args:
: flavor_id: The id of the flavor to update.
  flavor_update: The update to be applied to the flavor.

Returns:
: The updated flavor.

#### *abstract* update_model(model_id: UUID, model_update: [ModelUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelUpdate)) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Updates an existing model.

Args:
: model_id: UUID of the model to be updated.
  model_update: the Model to be updated.

Returns:
: The updated model.

#### *abstract* update_model_version(model_version_id: UUID, model_version_update_model: [ModelVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionUpdate)) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Get all model versions by filter.

Args:
: model_version_id: The ID of model version to be updated.
  model_version_update_model: The model version to be updated.

Returns:
: An updated model version.

Raises:
: KeyError: If the model version not found
  RuntimeError: If there is a model version with target stage,
  <br/>
  > but force flag is off

#### *abstract* update_pipeline(pipeline_id: UUID, pipeline_update: [PipelineUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineUpdate)) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Updates a pipeline.

Args:
: pipeline_id: The ID of the pipeline to be updated.
  pipeline_update: The update to be applied.

Returns:
: The updated pipeline.

Raises:
: KeyError: if the pipeline doesn’t exist.

#### *abstract* update_run(run_id: UUID, run_update: [PipelineRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunUpdate)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Updates a pipeline run.

Args:
: run_id: The ID of the pipeline run to update.
  run_update: The update to be applied to the pipeline run.

Returns:
: The updated pipeline run.

Raises:
: KeyError: if the pipeline run doesn’t exist.

#### *abstract* update_run_step(step_run_id: UUID, step_run_update: [StepRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunUpdate)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Updates a step run.

Args:
: step_run_id: The ID of the step to update.
  step_run_update: The update to be applied to the step.

Returns:
: The updated step run.

Raises:
: KeyError: if the step run doesn’t exist.

#### *abstract* update_run_template(template_id: UUID, template_update: [RunTemplateUpdate](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateUpdate)) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Updates a run template.

Args:
: template_id: The ID of the template to update.
  template_update: The update to apply.

Returns:
: The updated template.

Raises:
: KeyError: If the template does not exist.

#### *abstract* update_schedule(schedule_id: UUID, schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Updates a schedule.

Args:
: schedule_id: The ID of the schedule to be updated.
  schedule_update: The update to be applied.

Returns:
: The updated schedule.

Raises:
: KeyError: if the schedule doesn’t exist.

#### *abstract* update_secret(secret_id: UUID, secret_update: [SecretUpdate](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretUpdate)) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Updates a secret.

Secret values that are specified as None in the update that are
present in the existing secret are removed from the existing secret.
Values that are present in both secrets are overwritten. All other
values in both the existing secret and the update are kept (merged).

If the update includes a change of name or scope, the scoping rules
enforced in the secrets store are used to validate the update:

> - only one workspace-scoped secret with the given name can exist
>   in the target workspace.
> - only one user-scoped secret with the given name can exist in the
>   target workspace for the target user.

Args:
: secret_id: The ID of the secret to be updated.
  secret_update: The update to be applied.

Returns:
: The updated secret.

Raises:
: KeyError: if the secret doesn’t exist.
  EntityExistsError: If a secret with the same name already exists in
  <br/>
  > the same scope.

#### *abstract* update_server_settings(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate)) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Update the server settings.

Args:
: settings_update: The server settings update.

Returns:
: The updated server settings.

#### *abstract* update_service(service_id: UUID, update: [ServiceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceUpdate)) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Update an existing service.

Args:
: service_id: The ID of the service to update.
  update: The update to be applied to the service.

Returns:
: The updated service.

Raises:
: KeyError: if the service doesn’t exist.

#### *abstract* update_service_account(service_account_name_or_id: str | UUID, service_account_update: [ServiceAccountUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountUpdate)) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Updates an existing service account.

Args:
: service_account_name_or_id: The name or the ID of the service
  : account to update.
  <br/>
  service_account_update: The update to be applied to the service
  : account.

Returns:
: The updated service account.

Raises:
: KeyError: If no service account with the given name exists.

#### *abstract* update_service_connector(service_connector_id: UUID, update: [ServiceConnectorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorUpdate)) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Updates an existing service connector.

The update model contains the fields to be updated. If a field value is
set to None in the model, the field is not updated, but there are
special rules concerning some fields:

* the configuration and secrets fields together represent a full

valid configuration update, not just a partial update. If either is
set (i.e. not None) in the update, their values are merged together and
will replace the existing configuration and secrets values.
\* the resource_id field value is also a full replacement value: if set
to None, the resource ID is removed from the service connector.
\* the expiration_seconds field value is also a full replacement value:
if set to None, the expiration is removed from the service connector.
\* the secret_id field value in the update is ignored, given that
secrets are managed internally by the ZenML store.
\* the labels field is also a full labels update: if set (i.e. not
None), all existing labels are removed and replaced by the new labels
in the update.

Args:
: service_connector_id: The ID of the service connector to update.
  update: The update to be applied to the service connector.

Returns:
: The updated service connector.

Raises:
: KeyError: If no service connector with the given name exists.

#### *abstract* update_stack(stack_id: UUID, stack_update: [StackUpdate](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackUpdate)) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Update a stack.

Args:
: stack_id: The ID of the stack update.
  stack_update: The update request on the stack.

Returns:
: The updated stack.

Raises:
: KeyError: if the stack doesn’t exist.

#### *abstract* update_stack_component(component_id: UUID, component_update: [ComponentUpdate](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentUpdate)) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Update an existing stack component.

Args:
: component_id: The ID of the stack component to update.
  component_update: The update to be applied to the stack component.

Returns:
: The updated stack component.

Raises:
: KeyError: if the stack component doesn’t exist.

#### *abstract* update_tag(tag_name_or_id: str | UUID, tag_update_model: [TagUpdate](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagUpdate)) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Update tag.

Args:
: tag_name_or_id: name or id of the tag to be updated.
  tag_update_model: Tag to use for the update.

Returns:
: An updated tag.

Raises:
: KeyError: If the tag is not found

#### *abstract* update_trigger(trigger_id: UUID, trigger_update: [TriggerUpdate](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerUpdate)) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Update an existing trigger.

Args:
: trigger_id: The ID of the trigger to update.
  trigger_update: The update to be applied to the trigger.

Returns:
: The updated trigger.

Raises:
: KeyError: if the trigger doesn’t exist.

#### *abstract* update_user(user_id: UUID, user_update: [UserUpdate](zenml.models.v2.core.md#zenml.models.v2.core.user.UserUpdate)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Updates an existing user.

Args:
: user_id: The id of the user to update.
  user_update: The update to be applied to the user.

Returns:
: The updated user.

Raises:
: KeyError: If no user with the given name exists.

#### *abstract* update_workspace(workspace_id: UUID, workspace_update: [WorkspaceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceUpdate)) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Update an existing workspace.

Args:
: workspace_id: The ID of the workspace to be updated.
  workspace_update: The update to be applied to the workspace.

Returns:
: The updated workspace.

Raises:
: KeyError: if the workspace does not exist.

#### *abstract* verify_service_connector(service_connector_id: UUID, resource_type: str | None = None, resource_id: str | None = None, list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector instance has access to one or more resources.

Args:
: service_connector_id: The ID of the service connector to verify.
  resource_type: The type of resource to verify access to.
  resource_id: The ID of the resource to verify access to.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector and matching the supplied resource
  > type and ID are returned.

Returns:
: The list of resources that the service connector has access to,
  scoped to the supplied resource type and ID, if provided.

Raises:
: KeyError: If no service connector with the given name exists.
  NotImplementError: If the service connector cannot be verified
  <br/>
  > e.g. due to missing package dependencies.

#### *abstract* verify_service_connector_config(service_connector: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest), list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verifies if a service connector configuration has access to resources.

Args:
: service_connector: The service connector configuration to verify.
  list_resources: If True, the list of all resources accessible
  <br/>
  > through the service connector is returned.

Returns:
: The list of resources that the service connector configuration has
  access to.

Raises:
: NotImplementError: If the service connector cannot be verified
  : on the store e.g. due to missing package dependencies.

## Module contents

ZenStores define ways to store ZenML relevant data locally or remotely.
