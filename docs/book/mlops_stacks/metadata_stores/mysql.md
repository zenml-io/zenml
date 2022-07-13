---
description: Use a MySQL database service to store ML metadata 
---

The MySQL Metadata Store is a built-in ZenML [Metadata Store](./overview.md)
flavor that connects to a MySQL compatible service to store metadata
information.

## When would you want to use it?

Running ZenML pipelines with [the default SQLite Metadata Store](./sqlite.md) is
usually sufficient if you just want to evaluate ZenML or get started quickly
without incurring the trouble and the cost of managing additional services like
a self-hosted MySQL database or one of the managed cloud SQL database services.
However, the local SQLite Metadata Store becomes insufficient or unsuitable if
you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or
stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a
Kubeflow or Kubernetes Orchestrator running in public cloud).
* if you are running pipelines at scale and need a Metadata Store that can
handle the demands of production grade MLOps

In all these cases, you need a Metadata Store that is backed by a form of
public cloud or self-hosted MySQL database service.

You should use the MySQL Metadata Store when you need a shared, scalable and
performant Metadata Store and if you have access to a MySQL database service.
The database should ideally be accessible both from your local machine and the 
[Orchestrator](../orchestrators/overview.md) that you use in your ZenML stack. 
You should consider one of the other [Metadata Store flavors](./overview.md#metadata-store-flavors)
if you don't have access to a MySQL compatible database service.

## How do you deploy it?

Using the MySQL Metadata Store in your stack assumes that you already have
access to a MySQL database service. This can be an on-premise MySQL database
that you deployed explicitly for ZenML, or that you share with other services
in your team or organization. It can also be a managed MySQL compatible database
service deployed in the cloud.

{% hint style="info" %}
Configuring and deploying a managed MySQL database cloud service to use with
ZenML can be a complex and error prone process, especially if you plan on using
it alongside other stack components running in the cloud. You might consider
referring to the [ZenML Cloud Guide](../../cloud-guide/overview.md)
for a more holistic approach to configuring full cloud stacks for ZenML.
{% endhint %}

In order to connect to your MySQL instance, there are a few parameters that you
will need to configure and register a MySQL Metadata Store stack component. In
all cases you will need to set the following fields:

* `host` - The hostname or public IP address of your MySQL instance. This needs
to be reachable from your Orchestrator and, ideally, also from your local
machine.
* `port` - The port at which to reach the MySQL instance (default is 3306)
* `database` - The name of the database that will be used by ZenML to store
metadata information

Additional authentication related parameters need to be configured differently
depending on the chosen authentication method.

### Authentication Methods

{% tabs %}
{% tab title="Basic Authentication" %}

This option configures the username and password directly as stack component
attributes.

{% hint style="warning" %}
This is not recommended for production settings as the password is clearly 
accessible on your machine in clear text and communication with the database 
is unencrypted.
{% endhint %}

```shell
# Register the mysql metadata store
zenml metadata-store register mysql_metadata_store --flavor=mysql \ 
    --host=<database-host> --port=<port> --database=<database-name> \
    --username=<database-user> --password=<database-password>

# Register and set a stack with the new metadata store
zenml stack register custom_stack -m mysql_metadata_store ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets_managers/overview.md)
in your stack and configure a ZenML secret to store the username and password
credentials securely.

It is strongly recommended to also enable the use of SSL connections
in your database service and configure SSL related parameters:

* `ssl_ca` - The SSL CA server certificate associated with your MySQL server.
* `ssl_cert` and `ssl_key` - SSL client certificate and private key. Only
required if you set up client certificates for the MySQL service.

The MySQL credentials are configured as a ZenML secret that is referenced in the
Metadata Store configuration, e.g.:

```shell
# Register the MySQL metadata store
zenml metadata-store register mysql_metadata_store --flavor=mysql \
    --host=<database-host> --port=<port> --database=<database-name> \
    --secret=mysql_secret

# Register a secrets manager
zenml secrets-manager register secrets_manager \
    --flavor=<FLAVOR_OF_YOUR_CHOICE> ...
    
# Register and set a stack with the new metadata store and secret manager
zenml stack register custom_stack -m mysql_metadata_store ... \
    -x secrets_manager --set

# Create the secret referenced in the metadata store
zenml secret register mysql_secret --schema=mysql \ 
    --user=<database-user> --password=<database-password> \
    --ssl_ca=@path/to/server/ca/certificate \
    --ssl_cert=@path/to/client/certificate \
    --ssl_key=@path/to/client/certificate/key
```

{% endtab %}
{% endtabs %}

For more, up-to-date information on the MySQL Metadata Store implementation and its
configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.mysql_metadata_store).

## How do you use it?

Aside from the fact that the metadata information is stored in a MySQL database,
using the MySQL Metadata Store is no different than [using any other flavor of Metadata Store](./overview.md#how-to-use-it).
