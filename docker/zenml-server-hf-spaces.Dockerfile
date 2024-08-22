FROM zenmldocker/zenml-server:latest

ENV ZENML_ANALYTICS_OPT_IN=true
ENV ZENML_SERVER_DEPLOYMENT_TYPE="hf_spaces"

# fixes iframe / CORS issue for HF deployments
ENV ZENML_SERVER_SECURE_HEADERS_CSP="frame-ancestors *;"

################################################################################
#
# CONFIGURING YOUR ZENML HF SPACES SERVER
# ---------------------------------------
# By default this space is not persistent. All ZenML metadata is stored in
# localstorage in a SQLite database. If you would like to make your storage
# persistent, use the appropriate environment variables below to configure the
# image to use a MySQL-compatible database service that is reachable from the
# container. See
# https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-docker
# for more information on how to configure these environment variables.

# You can also configure the secrets store to use for your ZenML server. Be 
# sure to use Huggingface Spaces' 'Repository Secrets' feature to store any
# secrets referenced here. See
# https://huggingface.co/docs/hub/spaces-overview#managing-secrets for more
# information on how to configure these environment variables.

# ENV ZENML_DEFAULT_PROJECT_NAME=""
# ENV ZENML_STORE_URL=""
# ENV ZENML_STORE_SSL_CA=""
# ENV ZENML_STORE_SSL_CERT=""
# ENV ZENML_STORE_SSL_KEY=""
# ENV ZENML_STORE_SSL_VERIFY_SERVER_CERT=""

# ENV ZENML_LOGGING_VERBOSITY=""

# # SECRETS STORE CONFIGURATION
# ENV ZENML_SECRETS_STORE_TYPE=""
# ENV ZENML_SECRETS_STORE_ENCRYPTION_KEY=""
# ENV ZENML_SECRETS_STORE_CLASS_PATH=""
# ENV ZENML_SERVER_JWT_SECRET_KEY=""

# # AWS Secrets Store Configuration
# ENV ZENML_SECRETS_STORE_REGION_NAME=""
# ENV ZENML_SECRETS_STORE_AWS_ACCESS_KEY_ID=""
# ENV ZENML_SECRETS_STORE_AWS_SECRET_ACCESS_KEY=""
# ENV ZENML_SECRETS_STORE_AWS_SESSION_TOKEN=""

# # GCP Secrets Store Configuration
# ENV ZENML_SECRETS_STORE_PROJECT_ID=""
# ENV GOOGLE_APPLICATION_CREDENTIALS=""

# # Azure Secrets Store Configuration
# ENV ZENML_SECRETS_STORE_KEY_VAULT_NAME=""
# ENV ZENML_SECRETS_STORE_AZURE_CLIENT_ID=""
# ENV ZENML_SECRETS_STORE_AZURE_CLIENT_SECRET=""
# ENV ZENML_SECRETS_STORE_AZURE_TENANT_ID=""

# # Hashicorp Secrets Store Configuration
# ENV ZENML_SECRETS_STORE_VAULT_ADDR=""
# ENV ZENML_SECRETS_STORE_VAULT_TOKEN=""
# ENV ZENML_SECRETS_STORE_VAULT_NAMESPACE=""
# ENV ZENML_SECRETS_STORE_MAX_VERSIONS=""

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app", "--log-level", "debug", "--no-server-header"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]
