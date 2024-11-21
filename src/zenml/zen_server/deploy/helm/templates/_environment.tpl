{{/*
Helpers for environment variables configured in ZenML deployments and secrets store
*/}}


{{/*
ZenML store configuration options (non-secret values).

This template constructs a dictionary that is similar to the python values that
can be configured in the zenml.zen_store.sql_zen_store.SqlZenStoreConfiguration
class. Only non-secret values are included in this dictionary.

The dictionary is then converted into deployment environment variables by other
templates and inserted where it is needed.

The input is taken from a .ZenML dict that is passed to the template and
contains the values configured in the values.yaml file for the ZenML server.

Args:
  .ZenML: A dictionary with the ZenML configuration values configured for the
  ZenML server.
Returns:
  A dictionary with the non-secret values configured for the ZenML store.
*/}}
{{- define "zenml.storeConfigurationAttrs" -}}
{{- if .ZenML.database.url }}
type: sql
ssl_verify_server_cert: {{ .ZenML.database.sslVerifyServerCert | default "false" | quote }}
{{- if .ZenML.database.backupStrategy }}
backup_strategy: {{ .ZenML.database.backupStrategy | quote }}
{{- if eq .ZenML.database.backupStrategy "database" }}
backup_database: {{ .ZenML.database.backupDatabase | quote }}
{{- else if eq .ZenML.database.backupStrategy "dump-file" }}
backup_directory: "/backups"
{{- end }}
{{- end }}
{{- if .ZenML.database.poolSize }}
pool_size: {{ .ZenML.database.poolSize | quote }}
{{- end }}
{{- if .ZenML.database.maxOverflow }}
max_overflow: {{ .ZenML.database.maxOverflow | quote }}
{{- end }}
{{- end }}
{{- end }}


{{/*
ZenML store configuration options (secret values).

This template constructs a dictionary that is similar to the python values that
can be configured in the zenml.zen_store.sql_zen_store.SqlZenStoreConfiguration
class. Only secret values are included in this dictionary.

The dictionary is then converted into deployment environment variables by other
templates and inserted where it is needed.

The input is taken from a .ZenML dict that is passed to the template and
contains the values configured in the values.yaml file for the ZenML server.

Args:
  .ZenML: A dictionary with the ZenML configuration values configured for the
  ZenML server.
Returns:
  A dictionary with the secret values configured for the ZenML store.
*/}}
{{- define "zenml.storeSecretConfigurationAttrs" -}}
{{- if .ZenML.database.url }}
url: {{ .ZenML.database.url | quote }}
{{- if .ZenML.database.sslCa }}
ssl_ca: {{ .Files.Get .ZenML.database.sslCa }}
{{- end }}
{{- if .ZenML.database.sslCert }}
ssl_cert: {{ .Files.Get .ZenML.database.sslCert }}
{{- end }}
{{- if .ZenML.database.sslKey }}
ssl_key: {{ .Files.Get .ZenML.database.sslKey }}
{{- end }}
{{- end }}
{{- end }}


{{/*
Store configuration environment variables (non-secret values).

Passes the .Values.zenml dict as input to the `zenml.storeConfigurationAttrs`
template and converts the output into a dictionary of environment variables that
need to be configured for the store.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the non-secret environment variables that are configured for
  the store (i.e. keys starting with `ZENML_STORE_`).
*/}}
{{- define "zenml.storeEnvVariables" -}}
{{ $zenml := dict "ZenML" .Values.zenml }}
{{- range $k, $v := include "zenml.storeConfigurationAttrs" $zenml | fromYaml }}
ZENML_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}


{{/*
Store configuration environment variables (secret values).

Passes the .Values.zenml dict as input to the `zenml.storeSecretConfigurationAttrs`
template and converts the output into a dictionary of environment variables that
need to be configured for the store.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the secret environment variables that are configured for
  the store (i.e. keys starting with `ZENML_STORE_`).
*/}}
{{- define "zenml.storeSecretEnvVariables" -}}
{{ $zenml := dict "ZenML" .Values.zenml }}
{{- range $k, $v := include "zenml.storeSecretConfigurationAttrs" $zenml | fromYaml }}
ZENML_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{/*
ZenML server configuration options (non-secret values).

This template constructs a dictionary that is similar to the python values that
can be configured in the zenml.config.server_config.ServerConfiguration
class. Only non-secret values are included in this dictionary.

The dictionary is then converted into deployment environment variables by other
templates and inserted where it is needed.

The input is taken from a .ZenML dict that is passed to the template and
contains the values configured in the values.yaml file for the ZenML server.

Args:
  .ZenML: A dictionary with the ZenML configuration values configured for the
  ZenML server.
Returns:
  A dictionary with the non-secret values configured for the ZenML server.
*/}}
{{- define "zenml.serverConfigurationAttrs" -}}
auth_scheme: {{ .ZenML.authType | default .ZenML.auth.authType | quote }}
deployment_type: {{ .ZenML.deploymentType | default "kubernetes" }}
{{- if .ZenML.threadPoolSize }}
thread_pool_size: {{ .ZenML.threadPoolSize | quote }}
{{- end }}
{{- if .ZenML.auth.jwtTokenAlgorithm }}
jwt_token_algorithm: {{ .ZenML.auth.jwtTokenAlgorithm | quote }}
{{- end }}
{{- if .ZenML.auth.jwtTokenIssuer }}
jwt_token_issuer: {{ .ZenML.auth.jwtTokenIssuer | quote }}
{{- end }}
{{- if .ZenML.auth.jwtTokenAudience }}
jwt_token_audience: {{ .ZenML.auth.jwtTokenAudience | quote }}
{{- end }}
{{- if .ZenML.auth.jwtTokenLeewaySeconds }}
jwt_token_leeway_seconds: {{ .ZenML.auth.jwtTokenLeewaySeconds | quote }}
{{- end }}
{{- if .ZenML.auth.jwtTokenExpireMinutes }}
jwt_token_expire_minutes: {{ .ZenML.auth.jwtTokenExpireMinutes | quote }}
{{- end }}
{{- if .ZenML.auth.authCookieName }}
auth_cookie_name: {{ .ZenML.auth.authCookieName | quote }}
{{- end }}
{{- if .ZenML.auth.authCookieDomain }}
auth_cookie_domain: {{ .ZenML.auth.authCookieDomain | quote }}
{{- end }}
{{- if .ZenML.auth.corsAllowOrigins }}
cors_allow_origins: {{ join "," .ZenML.auth.corsAllowOrigins | quote }}
{{- end }}
{{- if .ZenML.auth.maxFailedDeviceAuthAttempts }}
max_failed_device_auth_attempts: {{ .ZenML.auth.maxFailedDeviceAuthAttempts | quote }}
{{- end }}
{{- if .ZenML.auth.deviceAuthTimeout }}
device_auth_timeout: {{ .ZenML.auth.deviceAuthTimeout | quote }}
{{- end }}
{{- if .ZenML.auth.deviceAuthPollingInterval }}
device_auth_polling_interval: {{ .ZenML.auth.deviceAuthPollingInterval | quote }}
{{- end }}
{{- if .ZenML.auth.deviceExpirationMinutes }}
device_expiration_minutes: {{ .ZenML.auth.deviceExpirationMinutes | quote }}
{{- end }}
{{- if .ZenML.auth.trustedDeviceExpirationMinutes }}
trusted_device_expiration_minutes: {{ .ZenML.auth.trustedDeviceExpirationMinutes | quote }}
{{- end }}
{{- if .ZenML.auth.externalLoginURL }}
external_login_url: {{ .ZenML.auth.externalLoginURL | quote }}
{{- end }}
{{- if .ZenML.auth.externalUserInfoURL }}
external_user_info_url: {{ .ZenML.auth.externalUserInfoURL | quote }}
{{- end }}
{{- if .ZenML.auth.externalCookieName }}
external_cookie_name: {{ .ZenML.auth.externalCookieName | quote }}
{{- end }}
{{- if .ZenML.auth.externalServerID }}
external_server_id: {{ .ZenML.auth.externalServerID | quote }}
{{- end }}
{{- if .ZenML.rootUrlPath }}
root_url_path: {{ .ZenML.rootUrlPath | quote }}
{{- end }}
{{- if .ZenML.serverURL }}
server_url: {{ .ZenML.serverURL | quote }}
{{- end }}
{{- if .ZenML.dashboardURL }}
dashboard_url: {{ .ZenML.dashboardURL | quote }}
{{- end }}
{{- if .ZenML.auth.rbacImplementationSource }}
rbac_implementation_source: {{ .ZenML.auth.rbacImplementationSource | quote }}
{{- end }}
{{- range $key, $value := .ZenML.secure_headers }}
secure_headers_{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}


{{/*
Server configuration environment variables (non-secret values).

Passes the .Values.zenml dict as input to the `zenml.serverConfigurationAttrs`
template and converts the output into a dictionary of environment variables that
need to be configured for the server.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the non-secret environment variables that are configured for
  the server (i.e. keys starting with `ZENML_SERVER_`).
*/}}
{{- define "zenml.serverEnvVariables" -}}
{{ $zenml := dict "ZenML" .Values.zenml }}
{{- range $k, $v := include "zenml.serverConfigurationAttrs" $zenml | fromYaml }}
ZENML_SERVER_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}


{{/*
Secrets store configuration options (non-secret values).

This template constructs a dictionary that is similar to the python values that
can be configured in the zenml.config.secrets_store_config.SecretsStoreConfiguration
subclasses for each secrets store type. Only non-secret values are included in
this dictionary.

The dictionary is then converted into deployment environment variables by other
templates and inserted where it is needed.

The input is taken from a .SecretsStore dict that is passed to the template and
contains the values configured in the values.yaml file for either the primary
secrets store or the backup secrets store.

Legacy support for passing the GCP secrets store credentials through the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable is addressed here and
converted into the corresponding `auth_method` and `auth_config` values for the
GCP secrets store. This allows all values to be handed over to the container
as environment variables, without the need to mount the credentials into the
container as a volume.

Args:
  .SecretsStore: A dictionary with the values configured for either the primary
    or the backup secrets store.
Returns:
  A dictionary with the non-secret values configured for the secrets store.
*/}}
{{- define "zenml.secretsStoreConfigurationAttrs" -}}
{{- if .SecretsStore.enabled }}
type: {{ .SecretsStore.type | quote }}
{{- if eq .SecretsStore.type "aws" }}
auth_method: {{ .SecretsStore.aws.authMethod | quote }}
{{- if .SecretsStore.aws.region_name }}
region_name: {{ .SecretsStore.aws.region_name | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "gcp" }}
{{- if .SecretsStore.gcp.google_application_credentials }}
auth_method: "service-account"
{{- else }}
auth_method: {{ .SecretsStore.gcp.authMethod | quote }}
{{- if .SecretsStore.gcp.project_id }}
project_id: {{ .SecretsStore.gcp.project_id | quote }}
{{- end }}
{{- end }}
{{- else if eq .SecretsStore.type "azure" }}
auth_method: {{ .SecretsStore.azure.authMethod | quote }}
key_vault_name: {{ .SecretsStore.azure.key_vault_name | quote }}
{{- else if eq .SecretsStore.type "hashicorp" }}
vault_addr: {{ .SecretsStore.hashicorp.vault_addr | quote }}
{{- if .SecretsStore.hashicorp.vault_namespace }}
vault_namespace: {{ .SecretsStore.hashicorp.vault_namespace | quote }}
{{- end }}
{{- if .SecretsStore.hashicorp.max_versions }}
max_versions: {{ .SecretsStore.hashicorp.max_versions | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "custom" }}
class_path: {{ .SecretsStore.custom.class_path | quote }}
{{- end }}
{{- else }}
type: none
{{- end }}
{{- end }}

{{/*
Legacy GCP secrets store configuration.

This template is used to support the legacy GCP secrets store credentials
attributes (`zenml.secretsStore.gcp.google_application_credentials` and
`zenml.secretsStore.gcp.project_id`) and convert them automatically into the
corresponding new-style `auth_config` values for the GCP secrets store.

Args:
  .SecretsStore: A dictionary with the values configured for either the primary
    or the backup secrets store.
Returns:
  A `zenml.secretsStore.gcp.authConfig` value computed from the legacy GCP
  secrets store credentials attributes.
*/}}
{{- define "zenml.legacyGCPSecretsStoreAuthConfig" -}}
project_id: {{ .SecretsStore.gcp.project_id | quote }}
service_account_json: {{ .SecretsStore.gcp.google_application_credentials | quote }}
{{- end }}


{{/*
Secrets store configuration options (secret values).

This template constructs a dictionary that is similar to the python values that
can be configured in the zenml.config.secrets_store_config.SecretsStoreConfiguration
subclasses for each secrets store type. Only secret configuration values are
included in this dictionary.

The dictionary is then converted into secret environment variables by other
templates and inserted where it is needed.

The input is taken from a .SecretsStore dict that is passed to the template and
contains the values configured in the values.yaml file for either the primary
secrets store or the backup secrets store.

Legacy support for passing the GCP secrets store credentials through the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable is addressed here and
converted into the corresponding `auth_method` and `auth_config` values for the
GCP secrets store. This allows all values to be handed over to the container
as environment variables, without the need to mount the credentials into the
container as a volume.

Args:
  .SecretsStore: A dictionary with the values configured for either the primary
    or the backup secrets store.
Returns:
  A dictionary with the secret values configured for the secrets store.
*/}}
{{- define "zenml.secretsStoreSecretConfigurationAttrs" -}}
{{- if .SecretsStore.enabled }}
{{- if eq .SecretsStore.type "sql" }}
{{- if .SecretsStore.sql.encryptionKey }}
encryption_key: {{ .SecretsStore.sql.encryptionKey | quote }}
{{- else if .SecretsStore.encryptionKey }}
encryption_key: {{ .SecretsStore.encryptionKey | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "aws" }}
{{- if .SecretsStore.aws.authConfig }}
auth_config: {{ .SecretsStore.aws.authConfig | toJson | quote }}
{{- end }}
{{- if .SecretsStore.aws.aws_access_key_id }}
aws_access_key_id: {{ .SecretsStore.aws.aws_access_key_id | quote }}
{{- end }}
{{- if .SecretsStore.aws.aws_secret_access_key }}
aws_secret_access_key: {{ .SecretsStore.aws.aws_secret_access_key | quote }}
{{- end }}
{{- if .SecretsStore.aws.aws_session_token }}
aws_session_token: {{ .SecretsStore.aws.aws_session_token | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "azure" }}
{{- if .SecretsStore.azure.authConfig }}
auth_config: {{ .SecretsStore.azure.authConfig | toJson | quote }}
{{- end }}
{{- if .SecretsStore.azure.azure_client_id }}
azure_client_id: {{ .SecretsStore.azure.azure_client_id | quote }}
{{- end }}
{{- if .SecretsStore.azure.azure_client_secret }}
azure_client_secret: {{ .SecretsStore.azure.azure_client_secret | quote }}
{{- end }}
{{- if .SecretsStore.azure.azure_tenant_id }}
azure_tenant_id: {{ .SecretsStore.azure.azure_tenant_id | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "gcp" }}
{{- if .SecretsStore.gcp.google_application_credentials }}
auth_config: {{ include "zenml.legacyGCPSecretsStoreAuthConfig" . | fromYaml | toJson | quote }}
{{- else if .SecretsStore.gcp.authConfig }}
auth_config: {{ .SecretsStore.gcp.authConfig | toJson | quote }}
{{- end }}
{{- else if eq .SecretsStore.type "hashicorp" }}
{{- if .SecretsStore.hashicorp.vault_token }}
vault_token: {{ .SecretsStore.hashicorp.vault_token | quote }}
{{- end }}
{{- end }}
{{- end }}
{{- end }}


{{/*
Primary secrets store environment variables (non-secret values).

Passes the .Values.zenml.secretsStore dict as input to the
`zenml.secretsStoreEnvVariables` template and converts the output into a
dictionary of environment variables that need to be configured for the primary
secrets store.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the non-secret environment variables that are configured for
  the primary secrets store (i.e. keys starting with `ZENML_SECRETS_STORE_`).
*/}}
{{- define "zenml.secretsStoreEnvVariables" -}}
{{ $secretsStore := dict "SecretsStore" .Values.zenml.secretsStore }}
{{- range $k, $v := include "zenml.secretsStoreConfigurationAttrs" $secretsStore | fromYaml }}
ZENML_SECRETS_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{/*
Primary secrets store environment variables (secret values).

Passes the .Values.zenml.secretsStore dict as input to the
`zenml.secretsStoreSecretEnvVariables` template and converts the output into a
dictionary of environment variables that need to be configured for the primary
secrets store as secrets.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the secret environment variables that are configured for
  the primary secrets store (i.e. keys starting with `ZENML_SECRETS_STORE_`).
*/}}
{{- define "zenml.secretsStoreSecretEnvVariables" -}}
{{ $secretsStore := dict "SecretsStore" .Values.zenml.secretsStore }}
{{- range $k, $v := include "zenml.secretsStoreSecretConfigurationAttrs" $secretsStore | fromYaml }}
ZENML_SECRETS_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{/*
Backup secrets store environment variables (non-secret values).

Passes the .Values.zenml.secretsStore dict as input to the
`zenml.secretsStoreEnvVariables` template and converts the output into a
dictionary of environment variables that need to be configured for the backup
secrets store.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the non-secret environment variables that are configured for
  the backup secrets store (i.e. keys starting with
  `ZENML_BACKUP_SECRETS_STORE_`).
*/}}
{{- define "zenml.backupSecretsStoreEnvVariables" -}}
{{ $secretsStore := dict "SecretsStore" .Values.zenml.backupSecretsStore }}
{{- range $k, $v := include "zenml.secretsStoreConfigurationAttrs" $secretsStore | fromYaml }}
ZENML_BACKUP_SECRETS_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}


{{/*
Backup secrets store environment variables (secret values).

Passes the .Values.zenml.secretsStore dict as input to the
`zenml.secretsStoreSecretEnvVariables` template and converts the output into a
dictionary of environment variables that need to be configured for the backup
secrets store as secrets.

Args:
  .Values: The values.yaml file for the ZenML deployment.
Returns:
  A dictionary with the secret environment variables that are configured for
  the backup secrets store (i.e. keys starting with
  `ZENML_BACKUP_SECRETS_STORE_`).
*/}}
{{- define "zenml.backupSecretsStoreSecretEnvVariables" -}}
{{ $secretsStore := dict "SecretsStore" .Values.zenml.backupSecretsStore }}
{{- range $k, $v := include "zenml.secretsStoreSecretConfigurationAttrs" $secretsStore | fromYaml}}
ZENML_BACKUP_SECRETS_STORE_{{ $k | upper }}: {{ $v | quote }}
{{- end }}
{{- end }}
