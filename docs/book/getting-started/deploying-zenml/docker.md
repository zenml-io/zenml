---
description: Deploying ZenML on cloud using Docker or Helm
---

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
    Set this variable to true to see debug logs from ZenML
- ANALYTICS_OPT_IN
    Whether you'd like to opt-in to help improve ZenML with
    anonymous data.
- ZENML_AUTH_TYPE
    The auth type to configure ZenML server with. 
    Example value: OAUTH2_PASSWORD_BEARER
- ZENML_SERVER_ROOT_URL_PATH
    The path on your host where you are deploying ZenML to.

- ZENML_DEFAULT_PROJECT_NAME
    The name of the default project in ZenML.
- ZENML_DEFAULT_USER_NAME
    The name of the default user name in ZenML.
- ZENML_DEFAULT_USER_PASSWORD
    The password to use for the default ZenML user.    

- ZENML_STORE_TYPE
    The type of backend store that you want to configure 
    ZenML with. Example value: sql
- ZENML_STORE_URL
    The URL for the backend store that you want to configure 
    ZenML with.
- ZENML_STORE_SSL_CA
    The server certificate.
- ZENML_STORE_SSL_CERT
    The client certificate.
- ZENML_STORE_SSL_KEY
    The client key.
- ZENML_STORE_SSL_VERIFY_SERVER_CERT
    Whether to verify SSL certificates for the server.    
```
You can set all of these variables in a file and then pass it to the `docker` CLI using the `--env-file` flag. More details in the [Docker documentation here](https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file).

### Run ZenML on Docker

Once all the environment variables are set, you can run the image locally using the following command:

```
docker run -it -d -p 8080:80 zenmldocker/zenml-server
```
    
You can check the logs of the container to verify if the server is up and depending on where you have deployed it, you can also access the dashboard at a `localhost` port (if running locally) or through some other service that exposes your container to the internet. 

### Using the ZenML CLI
If you don't want to set variables and configure ZenML with a custom backend, you can choose to use the local store configuration through the ZenML CLI: run the `up` command with the `--docker` flag.

```
zenml up --docker
```

This command deploys a ZenML server locally in a Docker container. The output shows the URL at which you can access your ZenML dashboard and server.
