---
description: Deploying ZenML in a container.
---

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

## ZenML Server Configuration Options

If you're planning on deploying a custom containerized ZenML server yourself,
you probably need to configure some settings for it like the database it should
use, the default user details and more. The ZenML server container image uses
sensible defaults, so you can simply start a container without worrying too much
about the configuration. However, if you're looking to connect the ZenML server
to an external MySQL database, or to persist the internal SQLite database, or
simply want to control other settings like the default account, you can do so
by customizing the container's environment variables.

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
- **ZENML_STORE_TYPE**:
    The type of backend store that you want to configure 
    ZenML with. This should always be set to "sql".
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
- **ZENML_LOGGING_VERBOSITY**:
    Use this variable to control the verbosity of logs inside the container.
    It can be set to one of the following values: `NOTSET`, `ERROR`, `WARN`,
    `INFO` (default), `DEBUG` or `CRITICAL`.

If none of the `ZENML_STORE_*` variables are set, the container will default to
creating and using a SQLite database file stored at `/zenml/.zenconfig/local_stores/default_zen_store/zenml.db`
inside the container. The `/zenml/.zenconfig/local_stores` base path where the
default SQLite database is located can optionally be overridden by setting the
`ZENML_LOCAL_STORES_PATH` environment variable to pint to a different path
(e.g. a persistent volume or directory that is mounted from the host).

### Advanced Server Configuration Options

These configuration options are not required for most use cases, but can be
useful in certain scenarios that require mirroring the same ZenML server
configuration across multiple container instances (e.g. a Kubernetes
deployment with multiple replicas):

- **ZENML_USER_ID**:
    This is a UUID value that is used to uniquely identify the server's
    identity (e.g. in analytics). If not explicitly set, it is generated
    automatically by the server and stored in the server's global configuration.
    This should be set to a random UUID value, e.g.:

     ```python
     from uuid import uuid4
     print(uuid4())
     ```

- **ZENML_JWT_SECRET_KEY**:
    This is a secret key used to sign JWT tokens used for authentication. If
    not explicitly set, a random key is generated automatically by the server
    and stored in the server's global configuration. This should be set to
    a random string with a recommended length of at least 32 characters, e.g.:
  
     ```python
     from secrets import token_hex
     token_hex(32)
     ```
    
    or:

     ```shell
     openssl rand -hex 32
     ```

## Run the ZenML server on Docker

As previously mentioned, the ZenML server container image uses sensible defaults
for most configuration options. This means that you can simply run the container
with Docker without any additional configuration and it will work out of the
box:

```
docker run -it -d -p 8080:80 zenmldocker/zenml-server
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
client to the server with:

```shell
zenml connect --url http://localhost:8080
```

If you are looking for a customized ZenML server Docker deployment, you can
configure one or more of [the supported environment variables](#zenml-server-configuration-options)
in a file and then pass it to the `docker` CLI using the `--env-file` flag (see
the [Docker documentation](https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file) for more details). For example:

```shell
docker run -it -d -p 8080:80 zenmldocker/zenml-server --env-file /path/to/env/file
```

The next sections cover a few relevant examples of ZenML Docker deployments
that you can use as a starting point for your own customized deployments.

### Persistent SQLite database

Depending on your use case, you may also want to mount a persistent volume or
directory from the host into the container to store the ZenML SQLite database
file. This can be done using the `--mount` flag (see the [Docker documentation](https://docs.docker.com/storage/volumes/) for more details). For example:

```shell
docker run -it -d -p 8080:80 zenmldocker/zenml-server --mount type=bind,source=/path/to/host/dir,target=/zenml/.zenconfig/local_stores
```


## Troubleshooting


You can check the logs of the container to verify if the server is up and depending on where you have deployed it, you can also access the dashboard at a `localhost` port (if running locally) or through some other service that exposes your container to the internet. 

