---
description: Deploying ZenML on cloud using Docker or Helm
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


If you wish to deploy ZenML on clouds other than AWS, Azure and GCP or on any other resource like a serverless platform or an on-prem Kubernetes cluster, you have two options:

- Using a Docker container.
- Using the Helm chart.

## Using Helm

The ZenML repository hosts a Helm chart that can be used to deploy to Kubernetes. This chart is not hosted on an online repository yet and so you can follow the steps below:

- Clone the `zenml-io/zenml` repository.

    ```
    git clone https://github.com/zenml-io/zenml.git
    ```
- Go into the directory that hosts the chart.

    ```
    cd src/zenml/zen_server/deploy/helm/
    ```

- Take a look at the `values.yaml` file to configure settings for your ZenML deployment. Make sure you have a MySQL database to use with the server and fill the `zenml.database` map with its values.

- Once everything is configured, you can now run the following command to create a release.
    ```
    helm -n <KUBERNETES_NAMESPACE> --create-namespace install zenml-server . 
    ```

> **Note**
> You will need to have an existing Kubernetes cluster and `kubectl` installed and configured, in addition to having `helm` itself.

## Connecting to deployed ZenML

Once ZenML is deployed, one or multiple users can connect to with the
`zenml connect` command. If no arguments are supplied, ZenML
will attempt to connect to the last ZenML server deployed from the local host using the `zenml deploy` command:

### ZenML Connect: Various options

```bash
zenml connect
```

To connect to a ZenML server, you can either pass the configuration as command
line arguments or as a YAML file:

```bash
zenml connect --url=https://zenml.example.com:8080 --username=admin --no-verify-ssl
```

or

```bash
zenml connect --config=/path/to/zenml_server_config.yaml
```

The YAML file should have the following structure when connecting to a ZenML
server:

```yaml
url: <The URL of the ZenML server>
username: <The username to use for authentication>
password: <The password to use for authentication>
verify_ssl: |
   <Either a boolean, in which case it controls whether the
   server's TLS certificate is verified, or a string, in which case it
   must be a path to a CA certificate bundle to use or the CA bundle
   value itself>
```

Example of a ZenML server YAML configuration file:

```yaml
url: https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com/zenml
username: admin
password: Pa$$word123
verify_ssl: |
-----BEGIN CERTIFICATE-----
MIIDETCCAfmgAwIBAgIQYUmQg2LR/pHAMZb/vQwwXjANBgkqhkiG9w0BAQsFADAT
MREwDwYDVQQDEwh6ZW5tbC1jYTAeFw0yMjA5MjYxMzI3NDhaFw0yMzA5MjYxMzI3
...
ULnzA0JkRWRnFqH6uXeJo1KAVqtxn1xf8PYxx3NlNDr9wi8KKwARf2lwm6sH4mvq
1aZ/0iYnGKCu7rLJzxeguliMf69E
-----END CERTIFICATE-----
```

Both options can be combined, in which case the command line arguments will
override the values in the YAML file. For example, it is possible and
recommended that you supply the password only as a command line argument:

```bash
zenml connect --username zenml --password=Pa@#$#word --config=/path/to/zenml_server_config.yaml
```

To disconnect from the current ZenML server and revert to using the local default database, use the following command:

```bash
zenml disconnect
```