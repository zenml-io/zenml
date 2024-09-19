# zenml.zen_server.routers package

## Submodules

## zenml.zen_server.routers.actions_endpoints module

## zenml.zen_server.routers.artifact_endpoint module

## zenml.zen_server.routers.artifact_version_endpoints module

## zenml.zen_server.routers.auth_endpoints module

## zenml.zen_server.routers.code_repositories_endpoints module

## zenml.zen_server.routers.devices_endpoints module

Endpoint definitions for code repositories.

### zenml.zen_server.routers.devices_endpoints.delete_authorized_device(device_id: UUID, auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → None

Deletes a specific OAuth2 authorized device using its unique ID.

Args:
: device_id: The ID of the OAuth2 authorized device to delete.
  auth_context: The current auth context.

Raises:
: KeyError: If the device with the given ID does not exist or does not
  : belong to the current user.

### zenml.zen_server.routers.devices_endpoints.get_authorization_device(device_id: UUID, user_code: str | None = None, hydrate: bool = True, auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Gets a specific OAuth2 authorized device using its unique ID.

Args:
: device_id: The ID of the OAuth2 authorized device to get.
  user_code: The user code of the OAuth2 authorized device to get. Needs
  <br/>
  > to be specified with devices that have not been verified yet.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.
  <br/>
  auth_context: The current auth context.

Returns:
: A specific OAuth2 authorized device object.

Raises:
: KeyError: If the device with the given ID does not exist, does not
  : belong to the current user or could not be verified using the
    given user code.

### zenml.zen_server.routers.devices_endpoints.list_authorized_devices(filter_model: [OAuthDeviceFilter](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceFilter) = Depends(init_cls_and_handle_errors), hydrate: bool = False, auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [Page](zenml.models.v2.base.md#id327)[[OAuthDeviceResponse](zenml.models.md#zenml.models.OAuthDeviceResponse)]

Gets a page of OAuth2 authorized devices belonging to the current user.

Args:
: filter_model: Filter model used for pagination, sorting,
  : filtering.
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.
  <br/>
  auth_context: The current auth context.

Returns:
: Page of OAuth2 authorized device objects.

### zenml.zen_server.routers.devices_endpoints.update_authorized_device(device_id: UUID, update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Updates a specific OAuth2 authorized device using its unique ID.

Args:
: device_id: The ID of the OAuth2 authorized device to update.
  update: The model containing the attributes to update.
  auth_context: The current auth context.

Returns:
: The updated OAuth2 authorized device object.

Raises:
: KeyError: If the device with the given ID does not exist or does not
  : belong to the current user.

### zenml.zen_server.routers.devices_endpoints.verify_authorized_device(device_id: UUID, request: [OAuthDeviceVerificationRequest](zenml.models.v2.misc.md#zenml.models.v2.misc.auth_models.OAuthDeviceVerificationRequest), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Verifies a specific OAuth2 authorized device using its unique ID.

This endpoint implements the OAuth2 device authorization grant flow as
defined in [https://tools.ietf.org/html/rfc8628](https://tools.ietf.org/html/rfc8628). It is called to verify
the user code for a given device ID.

If the user code is valid, the device is marked as verified and associated
with the user that authorized the device. This association is required to
be able to issue access tokens or revoke the device later on.

Args:
: device_id: The ID of the OAuth2 authorized device to update.
  request: The model containing the verification request.
  auth_context: The current auth context.

Returns:
: The updated OAuth2 authorized device object.

Raises:
: ValueError: If the device verification request fails.

## zenml.zen_server.routers.event_source_endpoints module

## zenml.zen_server.routers.flavors_endpoints module

## zenml.zen_server.routers.model_versions_endpoints module

## zenml.zen_server.routers.models_endpoints module

## zenml.zen_server.routers.pipeline_builds_endpoints module

## zenml.zen_server.routers.pipeline_deployments_endpoints module

## zenml.zen_server.routers.pipelines_endpoints module

## zenml.zen_server.routers.plugin_endpoints module

## zenml.zen_server.routers.run_metadata_endpoints module

## zenml.zen_server.routers.run_templates_endpoints module

## zenml.zen_server.routers.runs_endpoints module

## zenml.zen_server.routers.schedule_endpoints module

Endpoint definitions for pipeline run schedules.

### zenml.zen_server.routers.schedule_endpoints.delete_schedule(schedule_id: UUID, \_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → None

Deletes a specific schedule using its unique id.

Args:
: schedule_id: ID of the schedule to delete.

### zenml.zen_server.routers.schedule_endpoints.get_schedule(schedule_id: UUID, hydrate: bool = True, \_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Gets a specific schedule using its unique id.

Args:
: schedule_id: ID of the schedule to get.
  hydrate: Flag deciding whether to hydrate the output model(s)
  <br/>
  > by including metadata fields in the response.

Returns:
: A specific schedule object.

### zenml.zen_server.routers.schedule_endpoints.list_schedules(schedule_filter_model: [ScheduleFilter](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleFilter) = Depends(init_cls_and_handle_errors), hydrate: bool = False, \_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [Page](zenml.models.v2.base.md#id327)[[ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse)]

Gets a list of schedules.

Args:
: schedule_filter_model: Filter model used for pagination, sorting,
  : filtering
  <br/>
  hydrate: Flag deciding whether to hydrate the output model(s)
  : by including metadata fields in the response.

Returns:
: List of schedule objects.

### zenml.zen_server.routers.schedule_endpoints.update_schedule(schedule_id: UUID, schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate), \_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Updates the attribute on a specific schedule using its unique id.

Args:
: schedule_id: ID of the schedule to get.
  schedule_update: the model containing the attributes to update.

Returns:
: The updated schedule object.

## zenml.zen_server.routers.secrets_endpoints module

## zenml.zen_server.routers.server_endpoints module

Endpoint definitions for authentication (login).

### zenml.zen_server.routers.server_endpoints.activate_server(activate_request: [ServerActivationRequest](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerActivationRequest)) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse) | None

Updates a stack.

Args:
: activate_request: The request to activate the server.

Returns:
: The default admin user that was created during activation, if any.

### zenml.zen_server.routers.server_endpoints.get_onboarding_state(\_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → List[str]

Get the onboarding state of the server.

Returns:
: The onboarding state of the server.

### zenml.zen_server.routers.server_endpoints.get_settings(\_: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication), hydrate: bool = True) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Get settings of the server.

Args:
: hydrate: Whether to hydrate the response.

Returns:
: Settings of the server.

### zenml.zen_server.routers.server_endpoints.server_info() → [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)

Get information about the server.

Returns:
: Information about the server.

### zenml.zen_server.routers.server_endpoints.update_server_settings(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext) = Security(oauth2_authentication)) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Updates the settings of the server.

Args:
: settings_update: Settings update.
  auth_context: Authentication context.

Raises:
: IllegalOperationError: If trying to update admin properties without
  : admin permissions.

Returns:
: The updated settings.

### zenml.zen_server.routers.server_endpoints.version() → str

Get version of the server.

Returns:
: String representing the version of the server.

## zenml.zen_server.routers.service_accounts_endpoints module

## zenml.zen_server.routers.service_connectors_endpoints module

## zenml.zen_server.routers.service_endpoints module

## zenml.zen_server.routers.stack_components_endpoints module

## zenml.zen_server.routers.stack_deployment_endpoints module

## zenml.zen_server.routers.stacks_endpoints module

## zenml.zen_server.routers.steps_endpoints module

## zenml.zen_server.routers.tags_endpoints module

## zenml.zen_server.routers.triggers_endpoints module

## zenml.zen_server.routers.users_endpoints module

## zenml.zen_server.routers.webhook_endpoints module

## zenml.zen_server.routers.workspaces_endpoints module

## Module contents

Endpoint definitions.
