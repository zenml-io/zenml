---
description: Deploying ZenML in a Docker container.
---

# Deploy with Docker

The ZenML server container image is available at [`zenmldocker/zenml-server`](https://hub.docker.com/r/zenmldocker/zenml/) and can be used to deploy ZenML with a container management or orchestration tool like Docker and docker-compose, or a serverless platform like [Cloud Run](https://cloud.google.com/run), [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview), and more! This guide walks you through the various configuration options that the ZenML server container expects as well as a few deployment use cases.

## Try it out locally first

If you're just looking for a quick way to deploy the ZenML server using a container, without going through the hassle of interacting with a container management tool like Docker and manually configuring your container, you can use the ZenML CLI to do so. You only need to have Docker installed and running on your machine:

```bash
zenml login --local --docker
```

This command deploys a ZenML server locally in a Docker container, then connects your client to it. Similar to running plain `zenml login --local`, the server and the local ZenML client share the same SQLite database.

The rest of this guide is addressed to advanced users who are looking to manually deploy and manage a containerized ZenML server.

## ZenML server configuration options

If you're planning on deploying a custom containerized ZenML server yourself, you probably need to configure some settings for it like the **database** it should use, the **default user details,** and more. The ZenML server container image uses sensible defaults, so you can simply start a container without worrying too much about the configuration. However, if you're looking to connect the ZenML server to an external MySQL database or secrets management service, to persist the internal SQLite database, or simply want to control other settings like the default account, you can do so by customizing the container's environment variables.

The following environment variables can be passed to the container:

*   **ZENML\_STORE\_URL**: This URL should point to an SQLite database file _mounted in the container_, or to a MySQL-compatible database service _reachable from the container_. It takes one of these forms:

    ```
    sqlite:////path/to/zenml.db
    ```

    or:

    ```
    mysql://username:password@host:port/database
    ```
* **ZENML\_STORE\_SSL\_CA**: This can be set to a custom server CA certificate in use by the MySQL database service. Only valid when `ZENML_STORE_URL` points to a MySQL database that uses SSL-secured connections. The variable can be set either to the path where the certificate file is mounted inside the container or to the certificate contents themselves.
* **ZENML\_STORE\_SSL\_CERT**: This can be set to a client SSL certificate required to connect to the MySQL database service. Only valid when `ZENML_STORE_URL` points to a MySQL database that uses SSL-secured connections and requires client SSL certificates. The variable can be set either to the path where the certificate file is mounted inside the container or to the certificate contents themselves. This variable also requires `ZENML_STORE_SSL_KEY` to be set.
* **ZENML\_STORE\_SSL\_KEY**: This can be set to a client SSL private key required to connect to the MySQL database service. Only valid when `ZENML_STORE_URL` points to a MySQL database that uses SSL-secured connections and requires client SSL certificates. The variable can be set either to the path where the certificate file is mounted inside the container or to the certificate contents themselves. This variable also requires `ZENML_STORE_SSL_CERT` to be set.
* **ZENML\_STORE\_SSL\_VERIFY\_SERVER\_CERT**: This boolean variable controls whether the SSL certificate in use by the MySQL server is verified. Only valid when `ZENML_STORE_URL` points to a MySQL database that uses SSL-secured connections. Defaults to `False`.
* **ZENML\_LOGGING\_VERBOSITY**: Use this variable to control the verbosity of logs inside the container. It can be set to one of the following values: `NOTSET`, `ERROR`, `WARN`, `INFO` (default), `DEBUG` or `CRITICAL`.
* **ZENML\_STORE\_BACKUP\_STRATEGY**: This variable controls the database backup strategy used by the ZenML server. See the [Database backup and recovery](deploy-with-docker.md#database-backup-and-recovery) section for more details about this feature and other related environment variables. Defaults to `in-memory`.
* **ZENML\_SERVER\_RATE\_LIMIT\_ENABLED**: This variable controls the rate limiting for ZenML API (currently only for the `LOGIN` endpoint). It is disabled by default, so set it to `1` only if you need to enable rate limiting. To determine unique users a `X_FORWARDED_FOR` header or `request.client.host` is used, so before enabling this make sure that your network configuration is associating proper information with your clients in order to avoid disruptions for legitimate requests.
* **ZENML\_SERVER\_LOGIN\_RATE\_LIMIT\_MINUTE**: If rate limiting is enabled, this variable controls how many requests will be allowed to query the login endpoint in a one minute interval. Set it to a desired integer value; defaults to `5`.
* **ZENML\_SERVER\_LOGIN\_RATE\_LIMIT\_DAY**: If rate limiting is enabled, this variable controls how many requests will be allowed to query the login endpoint in an interval of day interval. Set it to a desired integer value; defaults to `1000`.

If none of the `ZENML_STORE_*` variables are set, the container will default to creating and using an SQLite database file stored at `/zenml/.zenconfig/local_stores/default_zen_store/zenml.db` inside the container. The `/zenml/.zenconfig/local_stores` base path where the default SQLite database is located can optionally be overridden by setting the `ZENML_LOCAL_STORES_PATH` environment variable to point to a different path (e.g. a persistent volume or directory that is mounted from the host).

### Secret store environment variables

Unless explicitly disabled or configured otherwise, the ZenML server will use the SQL database as [a secrets store backend](secret-management.md) where secret values are stored. If you want to use an external secrets management service like the AWS Secrets Manager, GCP Secrets Manager, Azure Key Vault, HashiCorp Vault or even your custom Secrets Store back-end implementation instead, you need to configure it explicitly using Docker environment variables. Depending on where you deploy your ZenML server and how your Kubernetes cluster is configured, you will also need to provide the credentials needed to access the secrets management service API.

> **Important:** If you are updating the configuration of your ZenML Server container to use a different secrets store back-end or location, you should follow [the documented secrets migration strategy](secret-management.md#secrets-migration-strategy) to minimize downtime and to ensure that existing secrets are also properly migrated.

{% tabs %}
{% tab title="Default" %}
The SQL database is used as the default secret store location. You only need to configure these options if you want to change the default behavior.

It is particularly recommended to enable encryption at rest for the SQL database if you plan on using it as a secrets store backend. You'll have to configure the secret key used to encrypt the secret values. If not set, encryption will not be used and passwords will be stored unencrypted in the database.

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `sql` in order to explicitly set this type of secret store.
*   **ZENML\_SECRETS\_STORE\_ENCRYPTION\_KEY**: the secret key used to encrypt all secrets stored in the SQL secrets store. It is recommended to set this to a random string with a length of at least 32 characters, e.g.:

    ```python
    from secrets import token_hex
    token_hex(32)
    ```

    or:

    ```shell
    openssl rand -hex 32
    ```

> **Important:** If you configure encryption for your SQL database secrets store, you should keep the `ZENML_SECRETS_STORE_ENCRYPTION_KEY` value somewhere safe and secure, as it will always be required by the ZenML server to decrypt the secrets in the database. If you lose the encryption key, you will not be able to decrypt the secrets in the database and will have to reset them.
{% endtab %}

{% tab title="AWS" %}
These configuration options are only relevant if you're using the AWS Secrets Manager as the secrets store backend.

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `aws` in order to set this type of secret store.

The AWS Secrets Store uses the ZenML AWS Service Connector under the hood to authenticate with the AWS Secrets Manager API. This means that you can use any of the [authentication methods supported by the AWS Service Connector](../../how-to/auth-management/aws-service-connector.md#authentication-methods) to authenticate with the AWS Secrets Manager API.

The minimum set of permissions that must be attached to the implicit or configured AWS credentials are: `secretsmanager:CreateSecret`, `secretsmanager:GetSecretValue`, `secretsmanager:DescribeSecret`, `secretsmanager:PutSecretValue`, `secretsmanager:TagResource` and `secretsmanager:DeleteSecret` and they must be associated with secrets that have a name starting with `zenml/` in the target region and account. The following IAM policy example can be used as a starting point:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ZenMLSecretsStore",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:CreateSecret",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:PutSecretValue",
                "secretsmanager:TagResource",
                "secretsmanager:DeleteSecret"
            ],
            "Resource": "arn:aws:secretsmanager:<AWS-region>:<AWS-account-id>:secret:zenml/*"
        }
    ]
}
```

The following configuration options are supported:

* **ZENML\_SECRETS\_STORE\_AUTH\_METHOD**: The AWS Service Connector authentication method to use (e.g. `secret-key` or `iam-role`).
* **ZENML\_SECRETS\_STORE\_AUTH\_CONFIG**: The AWS Service Connector configuration, in JSON format (e.g. `{"aws_access_key_id":"<aws-key-id>","aws_secret_access_key":"<aws-secret-key>","region":"<aws-region>"}`).

> **Note:** The remaining configuration options are deprecated and may be removed in a future release. Instead, you should set the `ZENML_SECRETS_STORE_AUTH_METHOD` and `ZENML_SECRETS_STORE_AUTH_CONFIG` variables to use the AWS Service Connector authentication method.

* **ZENML\_SECRETS\_STORE\_REGION\_NAME**: The AWS region to use. This must be set to the region where the AWS Secrets Manager service that you want to use is located.
* **ZENML\_SECRETS\_STORE\_AWS\_ACCESS\_KEY\_ID**: The AWS access key ID to use for authentication. This must be set to a valid AWS access key ID that has access to the AWS Secrets Manager service that you want to use. If you are using an IAM role attached to an EKS cluster to authenticate, you can omit this variable.
* **ZENML\_SECRETS\_STORE\_AWS\_SECRET\_ACCESS\_KEY**: The AWS secret access key to use for authentication. This must be set to a valid AWS secret access key that has access to the AWS Secrets Manager service that you want to use. If you are using an IAM role attached to an EKS cluster to authenticate, you can omit this variable.
{% endtab %}

{% tab title="GCP" %}
These configuration options are only relevant if you're using the GCP Secrets Manager as the secrets store backend.

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `gcp` in order to set this type of secret store.

The GCP Secrets Store uses the ZenML GCP Service Connector under the hood to authenticate with the GCP Secrets Manager API. This means that you can use any of the [authentication methods supported by the GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md#authentication-methods) to authenticate with the GCP Secrets Manager API.

The minimum set of permissions that must be attached to the implicit or configured GCP credentials are as follows:

* `secretmanager.secrets.create` for the target GCP project (i.e. no condition on the name prefix)
* `secretmanager.secrets.get`, `secretmanager.secrets.update`, `secretmanager.versions.access`, `secretmanager.versions.add` and `secretmanager.secrets.delete` for the target GCP project and for secrets that have a name starting with `zenml-`

This can be achieved by creating two custom IAM roles and attaching them to the principal (e.g. user or service account) that will be used to access the GCP Secrets Manager API with a condition configured when attaching the second role to limit access to secrets with a name prefix of `zenml-`. The following `gcloud` CLI command examples can be used as a starting point:

```bash
gcloud iam roles create ZenMLServerSecretsStoreCreator \
  --project <your GCP project ID> \
  --title "ZenML Server Secrets Store Creator" \
  --description "Allow the ZenML Server to create new secrets" \
  --stage GA \
  --permissions "secretmanager.secrets.create"

gcloud iam roles create ZenMLServerSecretsStoreEditor \
  --project <your GCP project ID> \
  --title "ZenML Server Secrets Store Editor" \
  --description "Allow the ZenML Server to manage its secrets" \
  --stage GA \
  --permissions "secretmanager.secrets.get,secretmanager.secrets.update,secretmanager.versions.access,secretmanager.versions.add,secretmanager.secrets.delete"

gcloud projects add-iam-policy-binding <your GCP project ID> \
  --member serviceAccount:<your GCP service account email> \
  --role projects/<your GCP project ID>/roles/ZenMLServerSecretsStoreCreator \
  --condition None

# NOTE: use the GCP project NUMBER, not the project ID in the condition
gcloud projects add-iam-policy-binding <your GCP project ID> \
  --member serviceAccount:<your GCP service account email> \
  --role projects/<your GCP project ID>/roles/ZenMLServerSecretsStoreEditor \
  --condition 'title=limit_access_zenml,description="Limit access to secrets with prefix zenml-",expression=resource.name.startsWith("projects/<your GCP project NUMBER>/secrets/zenml-")'
```

The following configuration options are supported:

* **ZENML\_SECRETS\_STORE\_AUTH\_METHOD**: The GCP Service Connector authentication method to use (e.g. `service-account`).
* **ZENML\_SECRETS\_STORE\_AUTH\_CONFIG**: The GCP Service Connector configuration, in JSON format (e.g. `{"project_id":"my-project","service_account_json":{ ... }}`).

> **Note:** The remaining configuration options are deprecated and may be removed in a future release. Instead, you should set the `ZENML_SECRETS_STORE_AUTH_METHOD` and `ZENML_SECRETS_STORE_AUTH_CONFIG` variables to use the GCP Service Connector authentication method.

* **ZENML\_SECRETS\_STORE\_PROJECT\_ID**: The GCP project ID to use. This must be set to the project ID where the GCP Secrets Manager service that you want to use is located.
* **GOOGLE\_APPLICATION\_CREDENTIALS**: The path to the GCP service account credentials file to use for authentication. This must be set to a valid GCP service account credentials file that has access to the GCP Secrets Manager service that you want to use. If you are using a GCP service account attached to a GKE cluster to authenticate, you can omit this variable. NOTE: the path to the credentials file must be mounted into the container.
{% endtab %}

{% tab title="Azure" %}
These configuration options are only relevant if you're using Azure Key Vault as the secrets store backend.

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `azure` in order to set this type of secret store.
* **ZENML\_SECRETS\_STORE\_KEY\_VAULT\_NAME**: The name of the Azure Key Vault. This must be set to point to the Azure Key Vault instance that you want to use.

The Azure Secrets Store uses the ZenML Azure Service Connector under the hood to authenticate with the Azure Key Vault API. This means that you can use any of the [authentication methods supported by the Azure Service Connector](../../how-to/auth-management/azure-service-connector.md#authentication-methods) to authenticate with the Azure Key Vault API. The following configuration options are supported:

* **ZENML\_SECRETS\_STORE\_AUTH\_METHOD**: The Azure Service Connector authentication method to use (e.g. `service-account`).
* **ZENML\_SECRETS\_STORE\_AUTH\_CONFIG**: The Azure Service Connector configuration, in JSON format (e.g. `{"tenant_id":"my-tenant-id","client_id":"my-client-id","client_secret": "my-client-secret"}`).

> **Note:** The remaining configuration options are deprecated and may be removed in a future release. Instead, you should set the `ZENML_SECRETS_STORE_AUTH_METHOD` and `ZENML_SECRETS_STORE_AUTH_CONFIG` variables to use the Azure Service Connector authentication method.

* **ZENML\_SECRETS\_STORE\_AZURE\_CLIENT\_ID**: The Azure application service principal client ID to use to authenticate with the Azure Key Vault API. If you are running the ZenML server hosted in Azure and are using a managed identity to access the Azure Key Vault service, you can omit this variable.
* **ZENML\_SECRETS\_STORE\_AZURE\_CLIENT\_SECRET**: The Azure application service principal client secret to use to authenticate with the Azure Key Vault API. If you are running the ZenML server hosted in Azure and are using a managed identity to access the Azure Key Vault service, you can omit this variable.
* **ZENML\_SECRETS\_STORE\_AZURE\_TENANT\_ID**: The Azure application service principal tenant ID to use to authenticate with the Azure Key Vault API. If you are running the ZenML server hosted in Azure and are using a managed identity to access the Azure Key Vault service, you can omit this variable.
{% endtab %}

{% tab title="Hashicorp" %}
These configuration options are only relevant if you're using Hashicorp Vault as the secrets store backend.

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `hashicorp` in order to set this type of secret store.
* **ZENML\_SECRETS\_STORE\_VAULT\_ADDR**: The URL of the HashiCorp Vault server to connect to. NOTE: this is the same as setting the `VAULT_ADDR` environment variable.
* **ZENML\_SECRETS\_STORE\_VAULT\_TOKEN**: The token to use to authenticate with the HashiCorp Vault server. NOTE: this is the same as setting the `VAULT_TOKEN` environment variable.
* **ZENML\_SECRETS\_STORE\_VAULT\_NAMESPACE**: The Vault Enterprise namespace. Not required for Vault OSS. NOTE: this is the same as setting the `VAULT_NAMESPACE` environment variable.
* **ZENML\_SECRETS\_STORE\_MAX\_VERSIONS**: The maximum number of secret versions to keep for each Vault secret. If not set, the default value of 1 will be used (only the latest version will be kept).
{% endtab %}

{% tab title="Custom" %}
These configuration options are only relevant if you're using a custom secrets store backend implementation. For this to work, you must have [a custom implementation of the secrets store API](manage-the-deployed-services/custom-secret-stores.md) in the form of a class derived from `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore`. This class must be importable from within the ZenML server container, which means you most likely need to mount the directory containing the class into the container or build a custom container image that contains the class.

The following configuration option is required:

* **ZENML\_SECRETS\_STORE\_TYPE:** Set this to `custom` in order to set this type of secret store.
* **ZENML\_SECRETS\_STORE\_CLASS\_PATH**: The fully qualified path to the class that implements the custom secrets store API (e.g. `my_package.my_module.MySecretsStore`).

If your custom secrets store implementation requires additional configuration options, you can pass them as environment variables using the following naming convention:

* `ZENML_SECRETS_STORE_<OPTION_NAME>`: The name of the option to pass to the custom secrets store class. The option name must be in uppercase and any hyphens (`-`) must be replaced with underscores (`_`). ZenML will automatically convert the environment variable name to the corresponding option name by removing the prefix and converting the remaining characters to lowercase. For example, the environment variable `ZENML_SECRETS_STORE_MY_OPTION` will be converted to the option name `my_option` and passed to the custom secrets store class configuration.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
**ZENML\_SECRETS\_STORE\_TYPE**: Set this variable to `none`to disable the secrets store functionality altogether.
{% endhint %}

#### Backup secrets store

[A backup secrets store](secret-management.md#backup-secrets-store) back-end may be configured for high-availability and backup purposes. or as an intermediate step in the process of [migrating secrets to a different external location or secrets manager provider](secret-management.md#secrets-migration-strategy).

To configure a backup secrets store in the Docker container, use the same approach and instructions documented for the primary secrets store, but set the `**ZENML\_BACKUP\_SECRETS\_STORE\***` environment variables instead of `**ZENML\_SECRETS\_STORE\***`, e.g.:

```yaml
ZENML_BACKUP_SECRETS_STORE_TYPE: aws
ZENML_BACKUP_SECRETS_STORE_AUTH_METHOD: secret-key
ZENML_BACKUP_SECRETS_STORE_AUTH_CONFIG: '{"aws_access_key_id":"<aws-key-id>", "aws_secret_access_key","<aws-secret-key>","role_arn": "<aws-role-arn>"}`'
```

### Advanced server configuration options

These configuration options are not required for most use cases, but can be useful in certain scenarios that require mirroring the same ZenML server configuration across multiple container instances (e.g. a Kubernetes deployment with multiple replicas):

*   **ZENML\_SERVER\_JWT\_SECRET\_KEY**: This is a secret key used to sign JWT tokens used for authentication. If not explicitly set, a random key is generated automatically by the server on startup and stored in the server's global configuration. This should be set to a random string with a recommended length of at least 32 characters, e.g.:

    ```python
    from secrets import token_hex
    token_hex(32)
    ```

    or:

    ```shell
    openssl rand -hex 32
    ```

The environment variables starting with _ZENML\_SERVER\_SECURE\_HEADERS\__\* can be used to enable, disable or set custom values for security headers in the ZenML server's HTTP responses. The following values can be set for any of the supported secure headers configuration options:

* `enabled`, `on`, `true` or `yes` - enables the secure header with the default value.
* `disabled`, `off`, `false`, `none` or `no` - disables the secure header entirely, so that it is not set in the ZenML server's HTTP responses.
* any other value - sets the secure header to the specified value.

The following secure headers environment variables are supported:

* **ZENML\_SERVER\_SECURE\_HEADERS\_SERVER**: The `Server` HTTP header value used to identify the server. The default value is the ZenML server ID.
* **ZENML\_SERVER\_SECURE\_HEADERS\_HSTS**: The `Strict-Transport-Security` HTTP header value. The default value is `max-age=63072000; includeSubDomains`.
* **ZENML\_SERVER\_SECURE\_HEADERS\_XFO**: The `X-Frame-Options` HTTP header value. The default value is `SAMEORIGIN`.
* **ZENML\_SERVER\_SECURE\_HEADERS\_XXP**: The `X-XSS-Protection` HTTP header value. The default value is `0`. NOTE: this header is deprecated and should not be customized anymore. The `Content-Security-Policy` header should be used instead.
* **ZENML\_SERVER\_SECURE\_HEADERS\_CONTENT**: The `X-Content-Type-Options` HTTP header value. The default value is `nosniff`.
* **ZENML\_SERVER\_SECURE\_HEADERS\_CSP**: The `Content-Security-Policy` HTTP header value. This is by default set to a strict CSP policy that only allows content from the origins required by the ZenML dashboard. NOTE: customizing this header is discouraged, as it may cause the ZenML dashboard to malfunction.
* **ZENML\_SERVER\_SECURE\_HEADERS\_REFERRER**: The `Referrer-Policy` HTTP header value. The default value is `no-referrer-when-downgrade`.
* **ZENML\_SERVER\_SECURE\_HEADERS\_CACHE**: The `Cache-Control` HTTP header value. The default value is `no-store, no-cache, must-revalidate`.
* **ZENML\_SERVER\_SECURE\_HEADERS\_PERMISSIONS**: The `Permissions-Policy` HTTP header value. The default value is `accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()`.

If you prefer to activate the server automatically during the initial deployment and also automate the creation of the initial admin user account, this legacy behavior can be brought back by setting the following environment variables:

* **ZENML\_SERVER\_AUTO\_ACTIVATE**: Set this to `1` to automatically activate the server and create the initial admin user account when the server is first deployed. Defaults to `0`.
* **ZENML\_DEFAULT\_USER\_NAME**: The name of the initial admin user account created by the server on the first deployment, during database initialization. Defaults to `default`.
* **ZENML\_DEFAULT\_USER\_PASSWORD**: The password to use for the initial admin user account. Defaults to an empty password value, if not set.

## Run the ZenML server with Docker

As previously mentioned, the ZenML server container image uses sensible defaults for most configuration options. This means that you can simply run the container with Docker without any additional configuration and it will work out of the box for most use cases:

```bash
docker run -it -d -p 8080:8080 --name zenml zenmldocker/zenml-server
```

> **Note:** It is recommended to use a ZenML container image version that matches the version of your client, to avoid any potential API incompatibilities (e.g. `zenmldocker/zenml-server:0.21.1` instead of `zenmldocker/zenml-server`).

The above command will start a containerized ZenML server running on your machine that uses a temporary SQLite database file stored in the container. Temporary means that the database and all its contents (stacks, pipelines, pipeline runs, etc.) will be lost when the container is removed with `docker rm`.

You need to visit the ZenML dashboard at `http://localhost:8080` and activate the server by creating an initial admin user account. You can then connect your client to the server with the web login flow:

```shell
$ zenml login http://localhost:8080
Connecting to: 'http://localhost:8080'...
If your browser did not open automatically, please open the following URL into your browser to proceed with the authentication:

http://localhost:8080/devices/verify?device_id=f7a7333a-3ef0-4f39-85a9-f190279456d3&user_code=9375f5cdfdaf36772ce981fe3ee6172c

Successfully logged in.
Creating default stack for user 'default'...
Updated the global store configuration.
```

{% hint style="info" %}
The `localhost` URL **will** work, even if you are using Docker-backed ZenML orchestrators in your stack, like [the local Docker orchestrator](../../component-guide/orchestrators/local-docker.md) or [a locally deployed Kubeflow orchestrator](../../component-guide/orchestrators/kubeflow.md).

ZenML makes use of specialized DNS entries such as `host.docker.internal` and `host.k3d.internal` to make the ZenML server accessible from the pipeline steps running inside other Docker containers on the same machine.
{% endhint %}

You can manage the container with the usual Docker commands:

* `docker logs zenml` to view the server logs
* `docker stop zenml` to stop the server
* `docker start zenml` to start the server again
* `docker rm zenml` to remove the container

If you are looking for a customized ZenML server Docker deployment, you can configure one or more of [the supported environment variables](deploy-with-docker.md#zenml-server-configuration-options) and then pass them to the container using the `docker run` `--env` or `--env-file` arguments (see the [Docker documentation](https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file) for more details). For example:

```shell
docker run -it -d -p 8080:8080 --name zenml \
    --env ZENML_STORE_URL=mysql://username:password@host:port/database \
    zenmldocker/zenml-server
```

If you're looking for a quick way to run both the ZenML server and a MySQL database with Docker, you can [deploy the ZenML server with Docker Compose](deploy-with-docker.md#zenml-server-with-docker-compose).

The rest of this guide covers various advanced use cases for running the ZenML server with Docker.

### Persisting the SQLite database

Depending on your use case, you may also want to mount a persistent volume or directory from the host into the container to store the ZenML SQLite database file. This can be done using the `--mount` flag (see the [Docker documentation](https://docs.docker.com/storage/volumes/) for more details). For example:

```shell
mkdir zenml-server
docker run -it -d -p 8080:8080 --name zenml \
    --mount type=bind,source=$PWD/zenml-server,target=/zenml/.zenconfig/local_stores/default_zen_store \
    zenmldocker/zenml-server
```

This deployment has the advantage that the SQLite database file is persisted even when the container is removed with `docker rm`.

### Docker MySQL database

As a recommended alternative to the SQLite database, you can run a MySQL database service as another Docker container and connect the ZenML server container to it.

A command like the following can be run to start the containerized MySQL database service:

```shell
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0
```

If you also wish to persist the MySQL database data, you can mount a persistent volume or directory from the host into the container using the `--mount` flag, e.g.:

```shell
mkdir mysql-data
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password \
    --mount type=bind,source=$PWD/mysql-data,target=/var/lib/mysql \
    mysql:8.0
```

Configuring the ZenML server container to connect to the MySQL database is just a matter of setting the `ZENML_STORE_URL` environment variable. We use the special `host.docker.internal` DNS name that is resolved from within the Docker containers to the gateway IP address used by the Docker network (see the [Docker documentation](https://docs.docker.com/desktop/networking/#use-cases-and-workarounds-for-all-platforms) for more details). On Linux, this needs to be explicitly enabled in the `docker run` command with the `--add-host` argument:

```shell
docker run -it -d -p 8080:8080 --name zenml \
    --add-host host.docker.internal:host-gateway \
    --env ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml \
    zenmldocker/zenml-server
```

You need to visit the ZenML dashboard at `http://localhost:8080` and activate the server by creating an initial admin user account. You can then connect your client to the server with the web login flow:

```shell
zenml login http://localhost:8080
```

### Direct MySQL database connection

This scenario is similar to the previous one, but instead of running a ZenML server, the client is configured to connect directly to a MySQL database running in a Docker container.

As previously covered, the containerized MySQL database service can be started with a command like the following:

```shell
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0
```

The ZenML client on the host machine can then be configured to connect directly to the database with a slightly different `zenml login` command:

```shell
zenml login mysql://root:password@127.0.0.1/zenml
```

> **Note** The `localhost` hostname will not work with MySQL databases. You need to use the `127.0.0.1` IP address instead.

### ZenML server with `docker-compose`

Docker compose offers a simpler way of managing multi-container setups on your local machine, which is the case for instance if you are looking to deploy the ZenML server container and connect it to a MySQL database service also running in a Docker container.

To use Docker Compose, you need to [install the docker-compose plugin](https://docs.docker.com/compose/install/linux/) on your machine first.

A `docker-compose.yml` file like the one below can be used to start and manage the ZenML server container and the MySQL database service all at once:

```yaml
version: "3.9"

services:
  mysql:
    image: mysql:8.0
    ports:
      - 3306:3306
    environment:
      - MYSQL_ROOT_PASSWORD=password
  zenml:
    image: zenmldocker/zenml-server
    ports:
      - "8080:8080"
    environment:
      - ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml
    links:
      - mysql
    depends_on:
      - mysql
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: on-failure
```

Note the following:

* `ZENML_STORE_URL` is set to the special Docker `host.docker.internal` hostname to instruct the server to connect to the database over the Docker network.
* The `extra_hosts` section is needed on Linux to make the `host.docker.internal` hostname resolvable from the ZenML server container.

To start the containers, run the following command from the directory where the `docker-compose.yml` file is located:

```shell
docker compose -p zenml up  -d
```

or, if you need to use a different filename or path:

```shell
docker compose -f /path/to/docker-compose.yml -p zenml up -d
```

You need to visit the ZenML dashboard at `http://localhost:8080` to activate the server by creating an initial admin account. You can then connect your client to the server with the web login flow:

```shell
zenml login http://localhost:8080
```

Tearing down the installation is as simple as running:

```shell
docker compose -p zenml down
```

## Database backup and recovery

An automated database backup and recovery feature is enabled by default for all Docker deployments. The ZenML server will automatically back up the database in-memory before every database schema migration and restore it if the migration fails.

{% hint style="info" %}
The database backup automatically created by the ZenML server is only temporary and only used as an immediate recovery in case of database migration failures. It is not meant to be used as a long-term backup solution. If you need to back up your database for long-term storage, you should use a dedicated backup solution.
{% endhint %}

Several database backup strategies are supported, depending on where and how the backup is stored. The strategy can be configured by means of the `ZENML_STORE_BACKUP_STRATEGY` environment variable:

* `disabled` - no backup is performed
* `in-memory` - the database schema and data are stored in memory. This is the fastest backup strategy, but the backup is not persisted across container restarts, so no manual intervention is possible in case the automatic DB recovery fails after a failed DB migration. Adequate memory resources should be allocated to the ZenML server container when using this backup strategy with larger databases. This is the default backup strategy.
* `database` - the database is copied to a backup database in the same database server. This requires the `ZENML_STORE_BACKUP_DATABASE` environment variable to be set to the name of the backup database. This backup strategy is only supported for MySQL compatible databases and the user specified in the database URL must have permissions to manage (create, drop, and modify) the backup database in addition to the main database.
* `dump-file` - the database schema and data are dumped to a filesystem location inside the ZenML server container. This location can be customized by means of the `ZENML_STORE_BACKUP_DIRECTORY` environment variable. When this strategy is configured, users should mount a host directory in the container and point the `ZENML_STORE_BACKUP_DIRECTORY` variable to where it's mounted inside the container. If a host directory is not mounted, the dump file will be stored in the container's filesystem and will be lost when the container is removed.

The following additional rules are applied concerning the creation and lifetime of the backup:

* a backup is not attempted if the database doesn't need to undergo a migration (e.g. when the ZenML server is upgraded to a new version that doesn't require a database schema change or if the ZenML version doesn't change at all).
* a backup file or database is created before every database migration attempt (i.e. when the container starts). If a backup already exists (i.e. persisted in a mounted host directory or backup database), it is overwritten.
* the persistent backup file or database is cleaned up after the migration is completed successfully or if the database doesn't need to undergo a migration. This includes backups created by previous failed migration attempts.
* the persistent backup file or database is NOT cleaned up after a failed migration. This allows the user to manually inspect and/or apply the backup if the automatic recovery fails.

The following example shows how to deploy the ZenML server to use a mounted host directory to persist the database backup file during a database migration:

```shell
mkdir mysql-data

docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password \
    --mount type=bind,source=$PWD/mysql-data,target=/var/lib/mysql \
    mysql:8.0

docker run -it -d -p 8080:8080 --name zenml \
    --add-host host.docker.internal:host-gateway \
    --mount type=bind,source=$PWD/mysql-data,target=/db-dump \
    --env ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml \
    --env ZENML_STORE_BACKUP_STRATEGY=dump-file \
    --env ZENML_STORE_BACKUP_DIRECTORY=/db-dump \
    zenmldocker/zenml-server
```

## Troubleshooting

You can check the logs of the container to verify if the server is up and, depending on where you have deployed it, you can also access the dashboard at a `localhost` port (if running locally) or through some other service that exposes your container to the internet.

### CLI Docker deployments

If you used the `zenml login --local --docker` CLI command to deploy the Docker ZenML server, you can check the logs with the command:

```shell
zenml logs -f
```

### Manual Docker deployments

If you used the `docker run` command to manually deploy the Docker ZenML server, you can check the logs with the command:

```shell
docker logs zenml -f
```

If you used the `docker compose` command to manually deploy the Docker ZenML server, you can check the logs with the command:

```shell
docker compose -p zenml logs -f
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
