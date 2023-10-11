---
description: Use a MySQL database to track your metadata non-locally 
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# Track your Metadata in the Cloud

While the local SQLite-based Metadata Store is a great default to get you 
started quickly, you will eventually need to move towards a deployed, shared 
and scalable database, for example once you switch to remote orchestration. 
This database will ideally be accessible both from your local machine, your 
orchestrator and the individual worker nodes of your orchestrator. 
A deployed MySQL Database can tick all these boxes. 

## Registering the MySQL Metadata Store

For the purpose of these docs it is assumed that the MySQL database is set up 
already. In order to connect to your MySQL instance there are a few parameters
that you will need to register a Metadata Store stack component.

In all cases you will need to set these three fields:

* host - The host IP address is the public IP address of your MySQL instance
* port - The port at which to reach the MySQL instance (default is 3306)
* database - The name of the database that will be used

For authentication, you'll have the choice of setting username and password 
directly to a stack component (not recommended for production setting), or 
you'll be able to register a secret in your secrets manager that allows you to 
also supply SSL certificates for more secure connections.

{% tabs %}
{% tab title="Basic Authentication" %}

{% hint style="warning" %}
This is not recommended for production settings as the password is easily 
accessible on your machine in clear text and communication with the database 
is unencrypted.
{% endhint %}

```shell
# Register the mysql-metadata-store
zenml metadata-store register mysql_metadata_store --flavor=mysql \ 
    --host=`<DB_HOST_IP>` --port=`<DB_PORT>` --database=`<DB_NAME>` \
    --username=`<DB_USERNAME>` --password`<DB_PASSWORD>`

# Register and set a stack with the new metadata store
zenml stack register cloud_stack -m mysql_metadata_store ... --set
```
{% endtab %}

{% tab title="Advanced Authentication" %}

For this option you will need to make sure to create and download all three
SSL certificates so that you can add them to a secret within the secrets 
manager of the stack that the MySQL Metadata Store is a part of.

```shell
# Register the mysql-metadata-store
zenml metadata-store register mysql_metadata_store --flavor=mysql \
    --host=`<DB_HOST_IP>` --port=`<DB_PORT>` --database=`<DB_NAME>` \
    --secret=mysql_secret

# Register a Secrets Manager
zenml secrets-manager register cloud_secrets_manager \
    --flavor=`<FLAVOR_OF_YOUR_CHOIC>` ...
    
# Register and set a stack with the new metadata store and secret manager
zenml stack register cloud_stack -m mysql_metadata_store ... \
    -x cloud_secrets_manager --set
    
zenml secret register mysql_secret --schema=mysql \ 
    --user=`<DB_USERNAME>` --password=`<DB_PASSWORD>` \
    --ssl_ca=@`</PATH/TO/DOWNLOADED/SERVER-CA>` \
    --ssl_cert=@`</PATH/TO/DOWNLOADED/CLIENT-CERT>` \
    --ssl_key=@`</PATH/TO/DOWNLOADED/CLIENT-KEY>`
```

{% hint style="info" %}
Depending on the cloud provider that you are running on, you will need to make 
sure the different stack components have the correct permissions and roles to 
access one another. The orchestrator in particular will need to have access to
the secrets manager.
{% endhint %}

{% endtab %}
{% endtabs %}

