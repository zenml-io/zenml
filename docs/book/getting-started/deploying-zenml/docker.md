---
description: Deploying ZenML on cloud using Docker or Helm
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


If you wish to deploy ZenML on clouds other than AWS, Azure and GCP or on any other resource like a serverless platform or an on-prem Kubernetes cluster, you have two options:

- Using a Docker container.
- Using the Helm chart.

## Using Docker

The ZenML server image is available at `zenmldocker/zenml-server` and can be used in container services, serverless platforms like [Cloud Run](https://cloud.google.com/run), [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview) and more!


### Configure your ZenML Deployment

Before running your ZenML server, you need to configure some settings for it like the database it should use, the default user details and more. 
You can set the following as environment variables wherever you want to run your ZenML server Docker container.

```
- ZENML_DEBUG
    Set this variable to true to see debug logs from ZenML. This takes in a True
    or False (default) value.
- ANALYTICS_OPT_IN
    Whether you'd like to opt-in to help improve ZenML with
    anonymous data. This takes in a True (default) or False value.
- ZENML_AUTH_TYPE
    The authentication scheme that the ZenML server should use. You can use one
    of the following options:
    
    NO_AUTH - No authentication is done. The default user is assumed to be
        used for all requests made to the server.
    HTTP_BASIC - HTTP Basic authentication
    OAUTH2_PASSWORD_BEARER (default) - OAuth2 password bearer with JWT tokens.

    NOTE: currently, only the OAUTH2_PASSWORD_BEARER authentication scheme is
    known to work with the CLI and ZenML Dashboard. You should use the other
    schemes only if you intent to access the REST API directly.
    
- ZENML_DEFAULT_PROJECT_NAME
    The name of the default project created by the server on first deployment.
- ZENML_DEFAULT_USER_NAME
    The name of the default user account created by the server on first
    deployment.
- ZENML_DEFAULT_USER_PASSWORD
    The password to use for the default user account.    

- ZENML_STORE_TYPE
    The type of backend store that you want to configure 
    ZenML with. This should always be set to "sql".
- ZENML_STORE_URL
    This URL should point to a MysSQL compatible database. It takes the form:

        mysql://username:password@host:port/database

- ZENML_STORE_SSL_CA
    The server certificate in use by the MySQL database can be passed using this
    variable, if you are using SSL to connect to the database.
- ZENML_STORE_SSL_CERT
    The client certificate required to connect to the MySQL database, if you
    are using SSL client certificates to connect to the database.
- ZENML_STORE_SSL_KEY
    The client certificate private key required to connect to the MySQL
    database, if you are using SSL client certificates to connect to the
    database.
- ZENML_STORE_SSL_VERIFY_SERVER_CERT
    Whether to verify SSL certificate for the MySQL server.    
```
You can set all of these variables in a file and then pass it to the `docker` CLI using the `--env-file` flag. More details in the [Docker documentation here](https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file).

### Run ZenML on Docker

Once all the environment variables are set, you can run the image locally using the following command:

```
docker run -it -d -p 8080:80 zenmldocker/zenml-server --env-file /path/to/env/file
```
    
You can check the logs of the container to verify if the server is up and depending on where you have deployed it, you can also access the dashboard at a `localhost` port (if running locally) or through some other service that exposes your container to the internet. 

### Using the ZenML CLI
If you don't want to set variables and configure ZenML with a custom backend, you can choose to use the local store configuration through the ZenML CLI: run the `up` command with the `--docker` flag.

```
zenml up --docker
```

This command deploys a ZenML server locally in a Docker container. The output shows the URL at which you can access your ZenML dashboard and server.
