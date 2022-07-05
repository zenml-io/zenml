# GCP
To get started using ZenML on the cloud, you need some basic infrastructure up 
and running that you can then make more complicated depending on your use-case. 
This guide sets up the easiest MLOPs stack that we can run on GCP with ZenML. 

{% hint style="info" %}
This guide represents **one** of many ways to create a cloud stack on GCP. 
Every component could be replaced by a different implementation. Feel free to 
take this as your starting point.
{% endhint %}

## Prerequisites 

For this to work you need to have ZenML installed locally with all GCP 
requirements.

```bash
pip install zenml
zenml integration install gcp
```

Additionally, you will need Docker installed on your system. 

## The cloud stack

A full cloud stack will necessarily contain these five stack components:

* An **artifact store** to save all step output artifacts, in this guide we will
use a GCP bucket for this purpose
* A **metadata store** that keeps track of the relationships between artifacts, 
runs and parameters. In our case we will opt for a MySQL database on GCP
Cloud SQL.
* The **orchestrator** to run the pipelines. Here we will opt for a Vertex AI
pipelines orchestrator. This is a serverless GCP specific offering with minimal
hassle.
* A **container registry** for pushing and pulling the pipeline image.
* Finally, the **secrets Manager** to store passwords and SSL certificates.

## Step 1/10 Set up a GCP project (Optional)

As a first step it might make sense to 
[create](https://console.cloud.google.com/projectcreate) 
a separate GCP project for your ZenML resources. However, this step is 
completely optional, and you can also move forward within an existing project. 
If some resources already exist, feel free to skip their creation step and 
simply note down the relevant information. 

For simplicity, just
open up a terminal on the side and export relevant values as we go along. You
will use these when we set up the ZenML stack.
ZenML will use your project number at a later stage to connect to some 
resources, so let's export it. You'll most probably find it right 
[here](https://console.cloud.google.com/welcome).

```bash
export PROJECT_NUMBER=<PROJECT_NUMBER> # for example '492014921912'
```

## Step 2/10 Enable billing

Before moving on, you'll have to make sure you attach a billing account to 
your project. In case you do not have the permissions to do so, you'll have to
ask an organization administrator.
[Here](https://console.cloud.google.com/billing/projects) is a relevant page.

## Step 3/10 Enable Vertex AI

Vertex AI pipelines is at the heart of our GCP stack. As the orchestrator 
Vertex AI will run your pipelines and use all the other stack components. 
All you'll need to do at this stage is enable Vertex AI
[here](https://console.cloud.google.com/vertex-ai).

Once it is enabled you will see a drop-down with all the regions where 
Vertex AI is available. At this point it might make sense to make this 
decision for your ZenML Stack and export the full region name.

{% tabs %}
{% tab title="Unix Shell" %}
```shell
export GCP_LOCATION=<GCP_LOCATION> # for example 'europe-west3'
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:GCP_LOCATION=<GCP_LOCATION> # for example 'europe-west3'
```
{% endtab %}
{% endtabs %}

## Step 4/10 Enable Secrets Manager

The Secrets Manager will be needed so that the orchestrator will have secure
access to the other resources. 
[Here](https://console.cloud.google.com/marketplace/product/google/secretmanager.googleapis.com)
is where you'll be able to enable the secrets manager.

## Step 5/10 Enable Container Registry

The Vertex AI orchestrator uses Docker Images containing your pipeline code
for pipeline orchestration. For this to work you'll need to enable the GCP
Docker  registry 
[here](https://console.cloud.google.com/marketplace/product/google/containerregistry.googleapis.com).

In order to use the container registry at a later point you will need to 
set the container registry URI. This is how it is usually constructed:
`gcr.io/<PROJECT_ID>`. 


{% hint style="info" %}
The container registry has four options: `gcr.io` , `us.gcr.io`, `eu.gcr.io `, 
or `asia.gcr.io`. Choose the one appropriate for you. 
{% endhint %}


{% tabs %}
{% tab title="Unix Shell" %}
```bash
export CONTAINER_REGISTRY_URI=<CONTAINER_REGISTRY_URI> # for example 'eu.gcr.io/zenml-project'
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:CONTAINER_REGISTRY_URI=<CONTAINER_REGISTRY_URI> # for example 'eu.gcr.io/zenml-project'
```
{% endtab %}
{% endtabs %}

## Step 6/10 Set up Cloud Storage as Artifact Store

Storing of step artifacts is an important part of reproducible MLOps. 
Create a bucket [here](https://console.cloud.google.com/storage/create-bucket).

Within the configuration of the newly created bucket you can find the 
gsutil URI which you will need at a later point. It's usually going to look like 
this: `gs://<bucket-name>`

{% tabs %}
{% tab title="Unix Shell" %}
```bash
export GSUTIL_URI=<GSUTIL_URI> # for example 'gs://zenml_vertex_storage'
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:GSUTIL_URI=<GSUTIL_URI> # for example 'gs://zenml_vertex_storage'
```
{% endtab %}
{% endtabs %}

## Step 7/10 Set up a Cloud SQL instance as Metadata Store

One of the most complex resources that you'll need to manage is the MySQL
database. 

To start, we [create](https://console.cloud.google.com/sql/instances/create;engine=MySQLe)
a MySQL database. Once created, it will take some time for the database to be 
set up. 

Once it is set up you can find the IP-address. The password you set during 
creation of the instance is the root password. The default port for MySQL is 
3306. 

{% tabs %}
{% tab title="Unix Shell" %}
```bash
export DB_HOST_IP=<DB_HOST_IP> # for example '35.137.24.15'
export DB_PORT=<DB_PORT> # usually by default '3306'
export DB_USER=<DB_USER> # 'root' if you don't set up a separate user
export DB_PWD=<DB_PWD> # for example 'secure_root_pwd'
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:DB_HOST_IP=<DB_HOST_IP> # for example '35.137.24.15'
$Env:DB_PORT=<DB_PORT> # usually by default '3306'
$Env:DB_USER=<DB_USER> # 'root' if you don't set up a separate user
$Env:DB_PWD=<DB_PWD> # for example 'secure_root_pwd'
```
{% endtab %}
{% endtabs %}

Time to set up the connections to our database. To do this you'll need to go 
into the `Connections` menu. Under the `Networking` tab you'll need to add 
**0.0.0.0/0** to the authorized networks, thereby allowing all incoming traffic 
from everywhere. (Feel free to restrict this to your outgoing IP address)

For security reasons, it is also recommended to configure your database to only 
accept SSL connections. You'll find the relevant setting in the **Security** 
tab. Select **SSL Connections only** in order to encrypt all traffic with your 
database.

Now **Create Client Certificate** and download all three files. Export the paths 
to these three files as follows with a leading **@**.

{% tabs %}
{% tab title="Unix Shell" %}
```bash
export SSL_CA=@<SSL_CA> # for example @/home/zen/Downloads/server-ca.pem
export SSL_CERT=@<SSL_CERT> # for example @/home/zen/Downloads/client-cert.pem
export SSL_KEY=@<SSL_KEY> # for example @/home/zen/Downloads/client-key.pem
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:SSL_CA=@<SSL_CA> # for example @/home/zen/Downloads/server-ca.pem
$Env:SSL_CERT=@<SSL_CERT> # for example @/home/zen/Downloads/client-cert.pem
$Env:SSL_KEY=@<SSL_KEY> # for example @/home/zen/Downloads/client-key.pem
```
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
Note the **@** sign in front of these three variables. The **@** sign tells the 
secret manager that these are file paths to be loaded from.
{% endhint %}

Finally, head on over to the `Databases` submenu and create your database and
export its name. 

{% tabs %}
{% tab title="Unix Shell" %}
```bash
export DB_NAME=<DB_NAME> # for example zenml_db
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:DB_NAME=<DB_NAME> # for example zenml_db
```
{% endtab %}
{% endtabs %}

## Step 8/10 - Create a Service Account

All the resources are created. Now we need to make sure the instance performing 
the compute engine (Vertex AI) needs to have the relevant permissions to access 
the other resources. For this you'll need to go
[here](https://console.cloud.google.com/iam-admin/serviceaccounts/create) to 
create a service account. Give it a relevant name and allow access to the
following roles:

* Vertex AI Custom Code Service Agent
* Vertex AI Service Agent
* Container Registry Service Agent
* Secret Manager Admin

Also give your user access to the service account. This is the service account 
that will be used by the Vertex AI compute engine.

{% tabs %}
{% tab title="Unix Shell" %}
```bash
export SERVICE_ACCOUNT=<SERVICE_ACCOUNT> # for example zenml-vertex-sa@zenml-project.iam.gserviceaccount.com
```
{% endtab %}
{% tab title="Windows Powershell" %}
```shell
$Env:SERVICE_ACCOUNT=<SERVICE_ACCOUNT> # for example zenml-vertex-sa@zenml-project.iam.gserviceaccount.com
```
{% endtab %}
{% endtabs %}

On top of this we will also need to give permissions to the service account
of the custom code workers. 

For this, head over to your IAM 
[configurations](https://console.cloud.google.com/iam-admin/iam), click on 
**Include Google-provided role grants** on the top right and find the 
**<project_number>@gcp-sa-aiplatform-cc.iam.gserviceaccount.com** service
account. 

Now give this one the **Container Registry Service Agent** role on top of its 
existing role.

{% hint style="info" %}
This service account might not be present in the list of service accounts. In
that case, skip this part, and once your first pipeline run fails, return to 
this step in order to set the appropriate role.
{% endhint %}

## Step 9/10 Set Up `gcloud` CLI

Install the `gcloud` CLI on your machine. 
[Here](https://cloud.google.com/sdk/docs/install) is a guide on how to install 
it.

You will then also need to set the GCP project that you want to communicate 
with:

```bash
gcloud config set project $PROJECT_NUMBER
```

Additionally, you will need to configure Docker  with the following command:

```bash
gcloud auth configure-docker
```

## Step 10/10 ZenML Stack

Everything on the GCP side is set up, you're ready to set up the ZenML stack 
components now. 

Copy-paste this into your terminal and press enter.

```bash
zenml orchestrator register vertex_orchestrator --flavor=vertex \
      --project=$$PROJECT_NUMBER --location=$GCP_LOCATION \
      --workload_service_account=$SERVICE_ACCOUNT
zenml secrets-manager register gcp_secrets_manager \
      --flavor=gcp_secrets_manager --project_id=$PROJECT_NUMBER
zenml container-registry register gcp_registry --flavor=gcp \
      --uri=$CONTAINER_REGISTRY_URI
zenml artifact-store register gcp_artifact_store --flavor=gcp \
      --path=$GSUTIL_URI
zenml metadata-store register gcp_metadata_store --flavor=mysql \
      --host=$DB_HOST_IP --port=$DB_PORT --database=$DB_NAME \
      --secret=mysql_secret
zenml stack register gcp_vertex_stack -m gcp_metadata_store \
      -a gcp_artifact_store -o vertex_orchestrator -c gcp_registry \
      -x gcp_secrets_manager --set
zenml secret register mysql_secret --schema=mysql \
      --user=$DB_USER --password=$DB_PWD \
      --ssl_ca=$SSL_CA --ssl_cert=$SSL_CERT --ssl_key=$SSL_KEY
```

This is where your ZenML stack is created and connected to the GCP cloud 
resources. If you now run `zenml stack describe` you should see this:

```bash
            Stack Configuration             
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
┃ COMPONENT_TYPE     │ COMPONENT_NAME      ┃
┠────────────────────┼─────────────────────┨
┃ ARTIFACT_STORE     │ gcp_artifact_store  ┃
┠────────────────────┼─────────────────────┨
┃ CONTAINER_REGISTRY │ gcp_registry        ┃
┠────────────────────┼─────────────────────┨
┃ METADATA_STORE     │ gcp_metadata_store  ┃
┠────────────────────┼─────────────────────┨
┃ ORCHESTRATOR       │ vertex_orchestrator ┃
┠────────────────────┼─────────────────────┨
┃ SECRETS_MANAGER    │ gcp_secrets_manager ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛
     'gcp_vertex_stack' stack (ACTIVE)  
```

## Run your pipeline in the cloud

With your ZenML stack set up and active, you are now ready to run your ZenML
pipeline on Vertex AI. 

For example, you could pull the ZenML Vertex AI example and run it.

```bash
zenml example pull vertex_ai_orchestration
cd zenml_examples/vertex_ai_orchestration/
python run.py
```

At the end of the logs you should be seeing a link to the Vertex AI dashboard. 
It should look something like this:

![Finished Run](../assets/VertexAiRun.png)


## Conclusion

Within this guide you have set up and used a stack on GCP using the Vertex AI
orchestrator. For more guides on different cloud set-ups, check out the 
[Kubeflow](https://docs.zenml.io/advanced-guide/execute-pipelines-in-cloud) and 
[Kubernetes](https://blog.zenml.io/k8s-orchestrator/) orchestrators 
respectively and find out if these are a better fit for you.