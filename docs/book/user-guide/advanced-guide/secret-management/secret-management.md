---
description: Registering and utilizing secrets.
---

# Use the Secret Store

## What is a ZenML secret?

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks.

<figure><img src="../../../.gitbook/assets/SecretsInDashboard.png" alt=""><figcaption><p>List of Secrets managed through ZenML</p></figcaption></figure>

## Centralized secrets store

ZenML provides a centralized secrets management system that allows you to register and manage secrets in a secure way. In a local ZenML deployment, the secrets are stored in the local SQLite database. Once you are connected to a remote ZenML server, the secrets are stored in the secrets management back-end that the server is configured to use, but all access to the secrets is done through the ZenML server API.

Currently, the ZenML server can be configured to use one of the following supported secrets store back-ends:

* the SQL database that the ZenML server is using to store other managed objects such as pipelines, stacks, etc. This is the default option.
* the AWS Secrets Manager
* the GCP Secret Manager
* the Azure Key Vault
* the HashiCorp Vault
* a custom secrets store back-end implementation is also supported

Configuring the specific secrets store back-end that the ZenML server uses is done at deployment time. For more information on how to deploy a ZenML server and configure the secrets store back-end, refer to your deployment strategy inside the [deployment guide](../../../deploying-zenml/zenml-self-hosted/zenml-self-hosted.md).

If you are a [ZenML Cloud](https://zenml.io/cloud) user, you can configure your cloud backend based on your [deployment scenario](../../../deploying-zenml/zenml-cloud/cloud-system-architecture.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
