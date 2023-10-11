---
description: Deploying ZenML in a container.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The ZenML server container image is available at [`zenmldocker/zenml-server`](https://hub.docker.com/r/zenmldocker/zenml/)
and can be used to deploy ZenML with a container management or orchestration
tool like docker and docker-compose, or a serverless platform like [Cloud Run](https://cloud.google.com/run),
[Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview)
and more! This guide walks you through the various configuration options
that the ZenML server container expects as well as a few deployment use cases.

## Using the ZenML CLI

If you're just looking for a quick way to deploy the ZenML server using a
container, without going through the hassle of interacting with a container
management tool like docker and manually configuring your container, you can use
the ZenML CLI to do so. You only need to have Docker installed and running on
your machine:

```
zenml up --docker
```

This command deploys a ZenML server locally in a Docker container, then connects
your client to it. Similar to running plain `zenml up`, the server and the local
ZenML client share the same SQLite database.

The rest of this guide is addressed to advanced users who are looking to
manually deploy and manage a containerized ZenML server.

## ZenML Server Configuration Options

If you're planning on deploying a custom containerized ZenML server yourself,
you probably need to configure some settings for it like the database it should
use, the default user details and more. The ZenML server container image uses
sensible defaults, so you can simply start a container without worrying too much
about the configuration. However, if you're looking to connect the ZenML server
to an external MySQL database or secrets management service, or to persist the
internal SQLite database, or simply want to control other settings like the
default account, you can do so by customizing the container's environment
variables.

The following environment variables can be passed to the container:

- **ZENML_DEFAULT_PROJECT_NAME**:
    The name of the default project created by the server on first deployment,
    during database initialization. Defaults to `default`.
- **ZENML_DEFAULT_USER_NAME**:
    The name of the default admin user account created by the server on first
    deployment, during database initialization. Defaults to `default`.
- **ZENML_DEFAULT_USER_PASSWORD**:
    The password to use for the default admin user account. Defaults to an empty
    password value, if not set.
- **ZENML_STORE_URL**:
    This URL should point to a SQLite database file _mounted in the container_,
    or to a MySQL compatible database service _reachable from the container_. It
    takes one of the forms:

        sqlite:////path/to/zenml.db
    
    or:

        mysql://username:password@host:port/database
- **ZENML_STORE_SSL_CA**:
    This can be set to a custom server CA certificate in use by the MySQL
    database service. Only valid when `ZENML_STORE_URL` points to a MySQL
    database that uses SSL secured connections. The variable can be set either
    to the path where the certificate file is mounted inside the container
    or to the certificate contents themselves.
- **ZENML_STORE_SSL_CERT**:
    This can be set to a the client SSL certificate required to connect to the
    MySQL database service. Only valid when `ZENML_STORE_URL` points to a MySQL
    database that uses SSL secured connections and requires client SSL
    certificates. The variable can be set either to the path where the
    certificate file is mounted inside the container or to the certificate
    contents themselves. This variable also requires `ZENML_STORE_SSL_KEY` to be
    set.
- **ZENML_STORE_SSL_KEY**:
    This can be set to a the client SSL private key required to connect to the
    MySQL database service. Only valid when `ZENML_STORE_URL` points to a MySQL
    database that uses SSL secured connections and requires client SSL
    certificates. The variable can be set either to the path where the
    certificate file is mounted inside the container or to the certificate
    contents themselves. This variable also requires `ZENML_STORE_SSL_CERT` to
    be set.
- **ZENML_STORE_SSL_VERIFY_SERVER_CERT**:
    This boolean variable controls whether the SSL certificate in use by the
    MySQL server is verified. Only valid when `ZENML_STORE_URL` points to a
    MySQL database that uses SSL secured connections. Defaults to `False`.
- **ZENML_SECRETS_STORE_TYPE**:
    Set this variable to one of the supported secrets store types:

    - `none`: Use this value to disable the secrets store functionality.
    - `sql`: Use the ZenML SQL database as the secrets store. This is the
    default value. See the [SQL Secrets Store Configuration Options](#sql-secrets-store-configuration-options)
    section below for more configuration options.
    - `aws`: Use AWS Secrets Manager as the secrets store backend. See the
    [AWS Secrets Store Configuration Options](#aws-secrets-store-configuration-options)
    section below for more configuration options.
    - `gcp`: Use GCP Secrets Manager as the secrets store backend. See the
    [GCP Secrets Store Configuration Options](#gcp-secrets-store-configuration-options)
    section below for more configuration options.
    - `azure`: Use Azure Key Vault as the secrets store backend. See the
    [Azure Secrets Store Configuration Options](#azure-secrets-store-configuration-options)
    section below for more configuration options.
    - `hashicorp`: Use HashiCorp Vault as the secrets store backend. See the
    [HashiCorp Vault Secrets Store Configuration Options](#hashicorp-vault-secrets-store-configuration-options)
    - `custom`: Use a custom secrets store backend implementation. See the
    [Custom Secrets Store Configuration Options](#custom-secrets-store-configuration-options).

- **ZENML_LOGGING_VERBOSITY**:
    Use this variable to control the verbosity of logs inside the container.
    It can be set to one of the following values: `NOTSET`, `ERROR`, `WARN`,
    `INFO` (default), `DEBUG` or `CRITICAL`.

If none of the `ZENML_STORE_*` variables are set, the container will default to
creating and using a SQLite database file stored at `/zenml/.zenconfig/local_stores/default_zen_store/zenml.db`
inside the container. The `/zenml/.zenconfig/local_stores` base path where the
default SQLite database is located can optionally be overridden by setting the
`ZENML_LOCAL_STORES_PATH` environment variable to point to a different path
(e.g. a persistent volume or directory that is mounted from the host).

### SQL Secrets Store Configuration Options

These configuration options are only relevant if you're using the SQL database
as the secrets store backend. The SQL database is used by default, so you only
need to configure these options if you want to change the default behavior.

- **ZENML_SECRETS_STORE_ENCRYPTION_KEY**:
    This is a secret key used to encrypt all secrets stored in the SQL secrets
    store. If not set, encryption will not be used and passwords will be stored
    unencrypted in the database. This should be set to a random string with a
    recommended length of at least 32 characters, e.g.:
  
     ```python
     from secrets import token_hex
     token_hex(32)
     ```
    
    or:

     ```shell
     openssl rand -hex 32
     ```

> **Important**
> If you configure encryption for your SQL database secrets store, you should
keep the `ZENML_SECRETS_STORE_ENCRYPTION_KEY` value somewhere safe and secure,
as it will be required to decrypt the secrets in the database. If you lose the
encryption key, you will not be able to decrypt the secrets in the database and
will have to reset them.

### AWS Secrets Store Configuration Options

These configuration options are only relevant if you're using the AWS Secrets
Manager as the secrets store backend.

- **ZENML_SECRETS_STORE_REGION_NAME**:
    The AWS region to use. This must be set to the region where the AWS
    Secrets Manager service that you want to use is located.

- **ZENML_SECRETS_STORE_AWS_ACCESS_KEY_ID**:
    The AWS access key ID to use for authentication. This must be set to a valid
    AWS access key ID that has access to the AWS Secrets Manager service that
    you want to use. If you are using an IAM role attached to an EKS cluster to
    authenticate, you can omit this variable.
    NOTE: this is the same as setting the `AWS_ACCESS_KEY_ID` environment
    variable.

- **ZENML_SECRETS_STORE_AWS_SECRET_ACCESS_KEY**:
    The AWS secret access key to use for authentication. This must be set to a
    valid AWS secret access key that has access to the AWS Secrets Manager
    service that you want to use. If you are using an IAM role attached to an
    EKS cluster to authenticate, you can omit this variable.
    NOTE: this is the same as setting the `AWS_SECRET_ACCESS_KEY` environment
    variable.

- **ZENML_SECRETS_STORE_AWS_SESSION_TOKEN**:
    Optional AWS session token to use for authentication.
    NOTE: this is the same as setting the `AWS_SESSION_TOKEN` environment
    variable.

- **ZENML_SECRETS_STORE_SECRET_LIST_REFRESH_TIMEOUT**:
    AWS' [Secrets Manager](https://aws.amazon.com/secrets-manager) has a known
    issue where it does not immediately
    reflect new and updated secrets in the `list_secrets` results. To work
    around this issue, you can set this refresh timeout value to a non-zero value to
    get the ZenML server to wait after creating or updating an AWS secret
    until the changes are reflected in the secrets returned by
    `list_secrets` or the number of seconds specified by this value has
    elapsed. Defaults to `0` (disabled). Should not be set to a high value
    as it may cause thread starvation in the ZenML server on high load.

### GCP Secrets Store Configuration Options

These configuration options are only relevant if you're using the GCP Secrets
Manager as the secrets store backend.

- **ZENML_SECRETS_STORE_PROJECT_ID**:
    The GCP project ID to use. This must be set to the project ID where the GCP
    Secrets Manager service that you want to use is located.

- **GOOGLE_APPLICATION_CREDENTIALS**:
    The path to the GCP service account credentials file to use for
    authentication. This must be set to a valid GCP service account credentials
    file that has access to the GCP Secrets Manager service that you want to
    use. If you are using a GCP service account attached to a GKE cluster to
    authenticate, you can omit this variable.
    NOTE: the path to the credentials file must be mounted into the container.

### Azure Secrets Store Configuration Options

These configuration options are only relevant if you're using Azure Key Vault as
the secrets store backend.

- **ZENML_SECRETS_STORE_KEY_VAULT_NAME**:
    The name of the Azure Key Vault. This must be set to point to the Azure
    Key Vault instance that you want to use.

- **ZENML_SECRETS_STORE_AZURE_CLIENT_ID**:
    The Azure application service principal client ID to use to
    authenticate with the Azure Key Vault API. If you are running the ZenML
    server hosted in Azure and are using a managed identity to access the Azure
    Key Vault service, you can omit this variable.
    NOTE: this is the same as setting the `AZURE_CLIENT_ID` environment
    variable.

- **ZENML_SECRETS_STORE_AZURE_CLIENT_SECRET**:
    The Azure application service principal client secret to use to
    authenticate with the Azure Key Vault API. If you are running the ZenML
    server hosted in Azure and are using a managed identity to access the Azure
    Key Vault service, you can omit this variable.
    NOTE: this is the same as setting the `AZURE_CLIENT_SECRET` environment
    variable.

- **ZENML_SECRETS_STORE_AZURE_TENANT_ID**:
    The Azure application service principal tenant ID to use to
    authenticate with the Azure Key Vault API. If you are running the ZenML
    server hosted in Azure and are using a managed identity to access the Azure
    Key Vault service, you can omit this variable.
    NOTE: this is the same as setting the `AZURE_TENANT_ID` environment
    variable.

### Hashicorp Vault Secrets Store Configuration Options

These configuration options are only relevant if you're using Hashicorp Vault as
the secrets store backend.

- **ZENML_SECRETS_STORE_VAULT_ADDR**:
    The url of the HashiCorp Vault server to connect to.
    NOTE: this is the same as setting the `VAULT_ADDR` environment
    variable.

- **ZENML_SECRETS_STORE_VAULT_TOKEN**:
    The token to use to authenticate with the HashiCorp Vault server.
    NOTE: this is the same as setting the `VAULT_TOKEN` environment
    variable.

- **ZENML_SECRETS_STORE_VAULT_NAMESPACE**:
    The Vault Enterprise namespace. Not required for Vault OSS.
    NOTE: this is the same as setting the `VAULT_NAMESPACE` environment
    variable.

- **ZENML_SECRETS_STORE_MAX_VERSIONS**:
    The maximum number of secret versions to keep for each Vault secret. If not
    set, the default value of 1 will be used (only the latest version will be
    kept).

### Custom Secrets Store Configuration Options

These configuration options are only relevant if you're using a custom secrets
store backend implementation. For this to work, you must have
[a custom implementation of the secrets store API](../../starter-guide/production-fundamentals/secrets-management.md#build-your-own-custom-secrets-manager)
in the form of a class derived from
`zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore`. This
class must be importable from within the ZenML server container, which means
you most likely need to mount the directory containing the class into the
container or build a custom container image that contains the class.

The following configuration option is required:

- **ZENML_SECRETS_STORE_CLASS_PATH**:
    The fully qualified path to the class that implements the custom secrets
    store API (e.g. `my_package.my_module.MySecretsStore`).

If your custom secrets store implementation requires additional configuration
options, you can pass them as environment variables using the following naming
convention:

- `ZENML_SECRETS_STORE_<OPTION_NAME>`:
    The name of the option to pass to the custom secrets store class. The
    option name must be in uppercase and any hyphens (`-`) must be replaced
    with underscores (`_`). ZenML will automatically convert the environment
    variable name to the corresponding option name by removing the prefix
    and converting the remaining characters to lowercase. For example, the
    environment variable `ZENML_SECRETS_STORE_MY_OPTION` will be converted to
    the option name `my_option` and passed to the custom secrets store class
    configuration.

### Advanced Server Configuration Options

These configuration options are not required for most use cases, but can be
useful in certain scenarios that require mirroring the same ZenML server
configuration across multiple container instances (e.g. a Kubernetes
deployment with multiple replicas):

- **ZENML_JWT_SECRET_KEY**:
    This is a secret key used to sign JWT tokens used for authentication. If
    not explicitly set, a random key is generated automatically by the server
    on startup and stored in the server's global configuration. This should be
    set to a random string with a recommended length of at least 32 characters,
    e.g.:
  
     ```python
     from secrets import token_hex
     token_hex(32)
     ```
    
    or:

     ```shell
     openssl rand -hex 32
     ```

## Run the ZenML server with Docker

As previously mentioned, the ZenML server container image uses sensible defaults
for most configuration options. This means that you can simply run the container
with Docker without any additional configuration and it will work out of the
box for most use cases:

```
docker run -it -d -p 8080:8080 --name zenml zenmldocker/zenml-server
```

> **Note**
> It is recommended to use a ZenML container image version that matches the
> version of your client, to avoid any potential API incompatibilities (e.g.
> `zenmldocker/zenml-server:0.21.1` instead of `zenmldocker/zenml-server`).

The above command will start a containerized ZenML server running on your
machine that uses a temporary SQLite database file stored in the container.
Temporary means that the database and all its contents (stacks, pipelines,
pipeline runs etc.) will be lost when the container is removed with `docker rm`.

You can visit the ZenML dashboard at http://localhost:8080 or connect your
client to the server with the `default` username and empty password:

```shell
$ zenml connect --url http://localhost:8080
Connecting to: 'http://localhost:8080'...
Username: default
Password for user default (press ENTER for empty password) []: 
Updated the global store configuration.
```

{% hint style="info" %}
The `localhost` URL **will** work, even if you are using Docker-backed ZenML
orchestrators in your stack, like [the local Docker orchestrator](../../component-gallery/orchestrators/local-docker.md)
or [a locally deployed Kubeflow orchestrator](../../component-gallery/orchestrators/kubeflow.md).

ZenML makes use of specialized DNS entries such as `host.docker.internal` and
`host.k3d.internal` to make the ZenML server accessible from the pipeline
steps running inside other Docker containers on the same machine.
{% endhint %}

You can manage the container with the usual Docker commands:

* `docker logs zenml` to view the server logs
* `docker stop zenml` to stop the server
* `docker start zenml` to start the server again
* `docker rm zenml` to remove the container

If you are looking for a customized ZenML server Docker deployment, you can
configure one or more of [the supported environment variables](#zenml-server-configuration-options)
and then pass them to the container using the `docker run` `--env` or
`--env-file` arguments (see the [Docker documentation](https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file)
for more details). For example:

```shell
docker run -it -d -p 8080:8080 --name zenml \
    --env ZENML_STORE_URL=mysql://username:password@host:port/database \
    zenmldocker/zenml-server
```

If you're looking for a quick way to run both the ZenML server and a MySQL
database with Docker, you can [deploy the ZenML server with Docker Compose](#zenml-server-with-docker-compose).

The rest of this guide covers various advanced use cases for running the ZenML
server with Docker.

### Persisting the SQLite database

Depending on your use case, you may also want to mount a persistent volume or
directory from the host into the container to store the ZenML SQLite database
file. This can be done using the `--mount` flag (see the [Docker documentation](https://docs.docker.com/storage/volumes/)
for more details). For example:

```shell
mkdir zenml-server
docker run -it -d -p 8080:8080 --name zenml \
    --mount type=bind,source=$PWD/zenml-server,target=/zenml/.zenconfig/local_stores/default_zen_store \
    zenmldocker/zenml-server
```

This deployment has the advantage that the SQLite database file is persisted
even when the container is removed with `docker rm`.

### Docker MySQL database

As a recommended alternative to the SQLite database, you can run a MySQL
database service as another Docker container and connect the ZenML server
container to it.

A command like the following can be run to start the containerized MySQL
database service:

```shell
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0
```

If you also wish to persist the MySQL database data, you can mount a persistent
volume or directory from the host into the container using the `--mount` flag,
e.g.:

```shell
mkdir mysql-data
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password \
    --mount type=bind,source=$PWD/mysql-data,target=/var/lib/mysql \
    mysql:8.0
```

Configuring the ZenML server container to connect to the MySQL database is just
a matter of setting the `ZENML_STORE_URL` environment variable. We use the
special `host.docker.internal` DNS name resolved from within the Docker
containers to the gateway IP address used by the Docker network (see the
[Docker documentation](https://docs.docker.com/desktop/networking/#use-cases-and-workarounds-for-all-platforms)
for more details). On Linux, this needs to be explicitly enabled in the
`docker run` command with the `--add-host` argument:

```shell
docker run -it -d -p 8080:8080 --name zenml \
    --add-host host.docker.internal:host-gateway \
    --env ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml \
    zenmldocker/zenml-server
```

Connecting your client to the ZenML server is the same as before:

```shell
zenml connect --url http://localhost:8080 --username default --password ''
```

### Direct MySQL database connection

This scenario is similar to the previous one, but instead of running a ZenML
server, the client is configured to connect directly to a MySQL database running
in a Docker container.

As previously covered, the containerized MySQL database service can be started
with a command like the following:

```shell
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0
```

The ZenML client on the host machine can then be configured to connect directly
to the database with a slightly different `zenml connect` command:

```shell
zenml connect --url mysql://127.0.0.1/zenml --username root --password password
```

> **Note**
> The `localhost` hostname will not work with MySQL databases. You need
> to use the `127.0.0.1` IP address instead.

### ZenML server with Docker Compose

Docker compose offers a simpler way of managing multi-container setups on
your local machine, which is the case for instance if you are looking to deploy
the ZenML server container and connect it to a MySQL database service also
running in a Docker container.

To use Docker Compose, you need to [install the docker-compose plugin](https://docs.docker.com/compose/install/linux/)
on your machine first.

A `docker-compose.yml` file like the one below can be used to start and manage
the ZenML server container and the MySQL database service all at once:

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
      - ZENML_DEFAULT_USER_NAME=admin
      - ZENML_DEFAULT_USER_PASSWORD=zenml
    links:
      - mysql
    depends_on:
      - mysql
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: on-failure
```

Note the following:

- `ZENML_STORE_URL` is set to the special Docker `host.docker.internal` hostname
to instruct the server to connect to the database over the Docker network.
- The `extra_hosts` section is needed on Linux to make the `host.docker.internal`
hostname resolvable from the ZenML server container.
- This example also uses the `ZENML_DEFAULT_USER_NAME` and `ZENML_DEFAULT_USER_PASSWORD`
environment variables to customize the default account credentials.

To start the containers, run the following command from the directory where
the `docker-compose.yml` file is located:

```shell
docker-compose -p zenml up  -d
```

or, if you need to use a different filename or path:

```shell
docker-compose -f /path/to/docker-compose.yml -p zenml up -d
```

Connecting your client to the ZenML server is the same as before:

```shell
zenml connect --url http://localhost:8080 --username admin --password zenml
```

Tearing down the installation is as simple as running:

```shell
docker-compose -p zenml down
```

## Troubleshooting

You can check the logs of the container to verify if the server is up and,
depending on where you have deployed it, you can also access the dashboard at
a `localhost` port (if running locally) or through some other service that
exposes your container to the internet.

### CLI Docker Deployments

If you used the `zenml up --docker` CLI command to deploy the Docker ZenML
server, you can check the logs with the command:

```shell
zenml logs -f
```

### Manual Docker Deployments

If you used the `docker run` command to manually deploy the Docker ZenML server,
you can check the logs with the command:

```shell
docker logs zenml -f
```

If you used the `docker compose` command to manually deploy the Docker ZenML
server, you can check the logs with the command:

```shell
docker compose -p zenml logs -f
```

## Upgrading your ZenML server

To upgrade to a new version with docker, you would have to delete the existing container and then execute the docker run command again with the version of the `zenml-server` image that you want to use.

- Delete the existing ZenML container:
    
  ```bash
  # find your container ID
  docker ps
  ```
  
  ```bash
  # stop the container
  docker stop <CONTAINER_ID>
  
  # remove the container
  docker rm <CONTAINER_ID>
  ```
    
- Deploy the version of the `zenml-server` image that you want to use. Find all versions [here](https://hub.docker.com/r/zenmldocker/zenml-server/tags).

  ```bash
  docker run -it -d -p 8080:8080 --name <CONTAINER_NAME> zenmldocker/zenml-server:<VERSION>
  ```

If you wish to keep your data after the upgrade, you should choose to deploy the container either with a persistent storage or with an external MySQL instance. In all other cases, your data will be lost once the container is deleted and a new one is spun up.

>**Warning**
> If you wish to downgrade a server, make sure that the version of ZenML that you’re moving to has the same database schema. This is because reverse migration of the schema is not supported.