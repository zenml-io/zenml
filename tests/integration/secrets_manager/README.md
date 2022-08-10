# Secrets Manager Integration Tests

These tests can be used to test various Secrets Manager flavors.

## For AWS

* set up local AWS client and credentials.
* run with `pytest tests/integration/secrets_manager --secrets-manager-flavor aws`.
* the Secrets Manager will use the `eu-west-2` region, which is dedicated to
integration testing.

## For GCP

* create a GCP service account and a key with full access to the
`zenml-secrets-manager` project. Set the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable to point to the downloaded key JSON file.
* run with `pytest tests/integration/secrets_manager --secrets-manager-flavor gcp`.

## For HashiCorp Vault

* install vault on your system.
* start a vault development instance with `vault server --dev` and note
the cluster's address and token
* set the VAULT_ADDR and VAULT_TOKEN environment variables to the cluster
address and token
* run with `pytest tests/integration/secrets_manager --secrets-manager-flavor vault`.
