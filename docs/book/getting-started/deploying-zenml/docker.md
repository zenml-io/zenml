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
`ZENML_LOCAL_STORES_PATH` environment variable to point to a different path
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

## Run the ZenML server with Docker

As previously mentioned, the ZenML server container image uses sensible defaults
for most configuration options. This means that you can simply run the container
with Docker without any additional configuration and it will work out of the
box for most use cases:

```
docker run -it -d -p 8080:80 --name zenml zenmldocker/zenml-server
```

> **Note**
> It is recommended to use a ZenML container image version that matches the
> version of your client, to avoid any potential API incompatibilities (e.g.
> `zenmldocker/zenml-server:0.21.1` instead of `zenmldocker/zenml-server`).

The above command will start a containerized ZenML server running on your
machine that uses a temporary SQLite database file stored in the container,
with all the limitations that this entails (see the earlier warning).
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

{% hint style="warning" %}
The `localhost` URL will not work if you are using Docker based ZenML
orchestrators in your stack. In this case, you need to
[use an IP address that is reachable from other containers](#inter-container-communication)
instead of `localhost` when you connect your client to the server, e.g.:

```shell
zenml connect --url http://172.17.0.1:8080
```

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
docker run -it -d -p 8080:80 --name zenml \
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
docker run -it -d -p 8080:80 --name zenml \
    --mount type=bind,source=$PWD/zenml-server,target=/zenml/.zenconfig/local_stores/default_zen_store \
    zenmldocker/zenml-server
```

This deployment has the advantage that the SQLite database file is persisted
even when the container is removed with `docker rm`. However, it still suffers
from the limitations incurred by using a SQLite database backend (see the
earlier warning). The recommended way to deploy a containerized ZenML server
is to use a MySQL database backend instead, as described in the next section.

### Docker MySQL database

As a recommended alternative to the SQLite database, you can run a MySQL
database service as another Docker container and connect the ZenML server
container to it.

A command like the following can be run to start the containerized MySQL
database service:

```shell
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:5.7
```

If you also wish to persist the MySQL database data, you can mount a persistent
volume or directory from the host into the container using the `--mount` flag,
e.g.:

```shell
mkdir mysql-data
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password \
    --mount type=bind,source=$PWD/mysql-data,target=/var/lib/mysql \
    mysql:5.7
```

Configuring the ZenML server container to connect to the MySQL database is just
a matter of setting the `ZENML_STORE_URL` environment variable. We use the
special `host.docker.internal` DNS name resolved from within the Docker
containers to the gateway IP address used by the Docker network (see the
[Docker documentation](https://docs.docker.com/desktop/networking/#use-cases-and-workarounds-for-all-platforms)
for more details). On Linux, this needs to be explicitly enabled in the
`docker run` command with the `--add-host` argument:

```shell
docker run -it -d -p 8080:80 --name zenml \
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
docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:5.7
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
    image: mysql:5.7
    ports:
      - 3306:3306
    environment:
      - MYSQL_ROOT_PASSWORD=password
  zenml:
    image: zenmldocker/zenml-server
    ports:
      - "8080:80"
    environment:
      - ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml
      - ZENML_DEFAULT_USERNAME=admin
      - ZENML_DEFAULT_PASSWORD=zenml
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
to instruct the server to connect to the database over the Docker network. The
ZenML client knows how to handle the `host.docker.internal` hostname
differently depending on whether it is running on the host machine or in another
Docker container.
- The `extra_hosts` section is needed on Linux to make the `host.docker.internal`
hostname resolvable from the ZenML server container.
- This example also uses the `ZENML_DEFAULT_USERNAME` and `ZENML_DEFAULT_PASSWORD`
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
zenml connect --url http://localhost:8080 --username default --password ''
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