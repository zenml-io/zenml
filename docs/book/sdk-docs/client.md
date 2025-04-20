---
icon: plug
---

# Client

The ZenML Client provides a programmatic interface to interact with all ZenML resources. This page organizes the client methods into thematic groups, making it easier to find the methods you need for various ZenML operations.

## Session and Environment Management

Methods for managing ZenML repositories and sessions:

* [`Client.initialize`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.initialize)
* [`Client.get_instance`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_instance)
* [`Client.root`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.root)
* [`Client.activate_root`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.activate_root)
* [`Client.find_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.find_repository)
* [`Client.is_repository_directory`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.is_repository_directory)
* [`Client.is_inside_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.is_inside_repository)
* [`Client.uses_local_configuration`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.uses_local_configuration)

## Stack Management

Methods for managing ZenML stacks and stack components:

* [`Client.active_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.active_stack)
* [`Client.activate_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.activate_stack)
* [`Client.create_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_stack)
* [`Client.get_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_stack)
* [`Client.list_stacks`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_stacks)
* [`Client.update_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_stack)
* [`Client.delete_stack`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_stack)
* [`Client.create_stack_component`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_stack_component)
* [`Client.delete_stack_component`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_stack_component)
* [`Client.create_flavor`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_flavor)
* [`Client.delete_flavor`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_flavor)

## User and Workspace Management

Methods for managing ZenML users, workspaces, and projects:

* [`Client.active_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.active_user)
* [`Client.active_workspace`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.active_workspace)
* [`Client.create_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_user)
* [`Client.get_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_user)
* [`Client.list_users`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_users)
* [`Client.update_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_user)
* [`Client.delete_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_user)
* [`Client.deactivate_user`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.deactivate_user)
* [`Client.create_workspace`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_workspace)
* [`Client.delete_workspace`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_workspace)
* [`Client.create_project`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_project)
* [`Client.get_project`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_project)
* [`Client.list_projects`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_projects)
* [`Client.update_project`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_project)
* [`Client.delete_project`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_project)
* [`Client.set_active_project`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.set_active_project)

## Pipeline Management

Methods for managing ZenML pipelines, runs, and related resources:

* [`Client.create_pipeline`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_pipeline)
* [`Client.get_pipeline`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_pipeline)
* [`Client.list_pipelines`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_pipelines)
* [`Client.delete_pipeline`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_pipeline)
* [`Client.get_pipeline_run`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_pipeline_run)
* [`Client.list_pipeline_runs`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_pipeline_runs)
* [`Client.update_pipeline_run`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_pipeline_run)
* [`Client.delete_pipeline_run`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_pipeline_run)
* [`Client.create_run_template`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_run_template)
* [`Client.delete_run_template`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_run_template)
* [`Client.delete_schedule`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_schedule)
* [`Client.create_trigger`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_trigger)
* [`Client.delete_trigger`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_trigger)
* [`Client.delete_trigger_execution`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_trigger_execution)

## Model Management

Methods for managing ZenML models and model versions:

* [`Client.create_model`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_model)
* [`Client.get_model`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_model)
* [`Client.list_models`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_models)
* [`Client.update_model`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_model)
* [`Client.delete_model`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_model)
* [`Client.create_model_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_model_version)
* [`Client.get_model_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_model_version)
* [`Client.list_model_versions`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_model_versions)
* [`Client.update_model_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_model_version)
* [`Client.delete_model_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_model_version)
* [`Client.delete_all_model_version_artifact_links`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_all_model_version_artifact_links)
* [`Client.delete_model_version_artifact_link`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_model_version_artifact_link)
* [`Client.stage_model_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.stage_model_version)

## Artifacts Management

Methods for managing ZenML artifacts:

* [`Client.get_artifact`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_artifact)
* [`Client.get_artifact_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_artifact_version)
* [`Client.list_artifacts`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_artifacts)
* [`Client.update_artifact`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_artifact)
* [`Client.delete_artifact`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_artifact)
* [`Client.delete_artifact_version`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_artifact_version)

## Secret Management

Methods for managing ZenML secrets:

* [`Client.create_secret`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_secret)
* [`Client.get_secret`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_secret)
* [`Client.list_secrets`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_secrets)
* [`Client.update_secret`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_secret)
* [`Client.delete_secret`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_secret)
* [`Client.backup_secrets`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.backup_secrets)

## Services and Deployments

Methods for managing ZenML services, builds and deployments:

* [`Client.create_service`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_service)
* [`Client.get_service`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_service)
* [`Client.list_services`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_services)
* [`Client.update_service`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_service)
* [`Client.delete_service`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_service)
* [`Client.delete_build`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_build)
* [`Client.delete_deployment`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_deployment)

## Service Connectors and Accounts

Methods for managing ZenML service connectors and service accounts:

* [`Client.create_service_connector`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_service_connector)
* [`Client.delete_service_connector`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_service_connector)
* [`Client.create_service_account`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_service_account)
* [`Client.delete_service_account`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_service_account)

## Code Repository Management

Methods for managing code repositories:

* [`Client.create_code_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_code_repository)
* [`Client.get_code_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_code_repository)
* [`Client.list_code_repositories`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_code_repositories)
* [`Client.update_code_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_code_repository)
* [`Client.delete_code_repository`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_code_repository)

## Authentication and Access Management

Methods for managing authentication and access:

* [`Client.create_api_key`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_api_key)
* [`Client.get_api_key`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_api_key)
* [`Client.delete_api_key`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_api_key)
* [`Client.delete_authorized_device`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_authorized_device)

## Metadata and Tagging

Methods for managing metadata and tags:

* [`Client.create_run_metadata`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_run_metadata)
* [`Client.get_run_metadata`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_run_metadata)
* [`Client.list_run_metadata`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.list_run_metadata)
* [`Client.create_tag`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_tag)
* [`Client.delete_tag`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_tag)

## Event Sources and Actions

Methods for managing events and actions:

* [`Client.create_action`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_action)
* [`Client.delete_action`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_action)
* [`Client.create_event_source`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.create_event_source)
* [`Client.delete_event_source`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.delete_event_source)

## Server Administration

Methods for managing ZenML server settings:

* [`Client.get_settings`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.get_settings)
* [`Client.update_server_settings`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client.update_server_settings)
