---
description: Configuring the secrets store.
---

# Secret store configuration and management

## Centralized secrets store

ZenML provides a centralized secrets management system that allows you to register and manage secrets in a secure way. The metadata of the ZenML secrets (e.g. name, ID, owner, scope etc.) is always stored in the ZenML server database, while the actual secret values are stored and managed separately, through the ZenML Secrets Store. This allows for a flexible deployment strategy that meets the security and compliance requirements of your organization.

In a local ZenML deployment, secret values are also stored in the local SQLite database. When connected to a remote ZenML server, the secret values are stored in the secrets management back-end that the server's Secrets Store is configured to use, while all access to the secrets is done through the ZenML server API.

<figure><img src="../../.gitbook/assets/secrets-store-architecture.png" alt=""><figcaption><p>Basic Secrets Store Architecture</p></figcaption></figure>

Currently, the ZenML server can be configured to use one of the following supported secrets store back-ends:

* the same SQL database that the ZenML server is using to store secrets metadata as well as other managed objects such as pipelines, stacks, etc. This is the default option.
* the AWS Secrets Manager
* the GCP Secret Manager
* the Azure Key Vault
* the HashiCorp Vault
* a custom secrets store back-end implementation is also supported

## Configuration and deployment

Configuring the specific secrets store back-end that the ZenML server uses is done at deployment time. This involves deciding on one of the supported back-ends and authentication mechanisms and configuring the ZenML server with the necessary credentials to authenticate with the back-end.

The ZenML secrets store reuses the [ZenML Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) authentication mechanisms to authenticate with the secrets store back-end. This means that the same authentication methods and configuration parameters that are supported by the available Service Connectors are also reflected in the ZenML secrets store configuration. It is recommended to practice the principle of least privilege when configuring the ZenML secrets store and to use credentials with the documented minimum required permissions to access the secrets store back-end.

The ZenML secrets store configured for the ZenML Server can be updated at any time by updating the ZenML Server configuration and redeploying the server. This allows you to easily switch between different secrets store back-ends and authentication mechanisms. However, it is recommended to follow [the documented secret store migration strategy](secret-management.md#secrets-migration-strategy) to minimize downtime and to ensure that existing secrets are also properly migrated, in case the location where secrets are stored in the back-end changes.

For more information on how to deploy a ZenML server and configure the secrets store back-end, refer to your deployment strategy inside the deployment guide.

## Backup secrets store

The ZenML Server deployment may be configured to optionally connect to _a second Secrets Store_ to provide additional features such as high-availability, backup and disaster recovery as well as an intermediate step in the process of migrating [secrets from one secrets store location to another](secret-management.md#secrets-migration-strategy). For example, the primary Secrets Store may be configured to use the internal database, while the backup Secrets Store may be configured to use the AWS Secrets Manager. Or two different AWS Secrets Manager accounts or regions may be used.

{% hint style="warning" %}
Always make sure that the backup Secrets Store is configured to use a different location than the primary Secrets Store. The location can be different in terms of the Secrets Store back-end type (e.g. internal database vs. AWS Secrets Manager) or the actual location of the Secrets Store back-end (e.g. different AWS Secrets Manager account or region, GCP Secret Manager project or Azure Key Vault's vault).

Using the same location for both the primary and backup Secrets Store will not provide any additional benefits and may even result in unexpected behavior.
{% endhint %}

When a backup secrets store is in use, the ZenML Server will always attempt to read and write secret values from/to the primary Secrets Store first while ensuring to keep the backup Secrets Store in sync. If the primary Secrets Store is unreachable, if the secret values are not found there or any otherwise unexpected error occurs, the ZenML Server falls back to reading and writing from/to the backup Secrets Store. Only if the backup Secrets Store is also unavailable, the ZenML Server will return an error.

In addition to the hidden backup operations, users can also explicitly trigger a backup operation by using the `zenml secret backup` CLI command. This command will attempt to read all secrets from the primary Secrets Store and write them to the backup Secrets Store. Similarly, the `zenml secret restore` CLI command can be used to restore secrets from the backup Secrets Store to the primary Secrets Store. These CLI commands are useful for migrating secrets from one Secrets Store to another.

## Secrets migration strategy

Sometimes you may need to change the external provider or location where secrets values are stored by the Secrets Store. The immediate implication of this is that the ZenML server will no longer be able to access existing secrets with the new configuration until they are also manually copied to the new location. Some examples of such changes include:

* switching Secrets Store back-end types (e.g. from internal SQL database to AWS Secrets Manager or Azure Key Vault)
* switching back-end locations (e.g. changing the AWS Secrets Manager account or region, GCP Secret Manager project or Azure Key Vault's vault).

In such cases, it is not sufficient to simply reconfigure and redeploy the ZenML server with the new Secrets Store configuration. This is because the ZenML server will not automatically migrate existing secrets to the new location. Instead, you should follow a specific migration strategy to ensure that existing secrets are also properly migrated to the new location with minimal, even zero downtime.

The secrets migration process makes use of the fact that [a secondary Secrets Store](secret-management.md#backup-secrets-store) can be configured for the ZenML server for backup purposes. This secondary Secrets Store is used as an intermediate step in the migration process. The migration process is as follows (we'll refer to the Secrets Store that is currently in use as _Secrets Store A_ and the Secrets Store that will be used after the migration as _Secrets Store B_):

1. Re-configure the ZenML server to use _Secrets Store B_ as the secondary Secrets Store.
2. Re-deploy the ZenML server.
3. Use the `zenml secret backup` CLI command to back up all secrets from _Secrets Store A_ to _Secrets Store B_. You don't have to worry about secrets that are created or updated by users during or after this process, as they will be automatically backed up to _Secrets Store B_. If you also wish to delete secrets from _Secrets Store A_ after they are successfully backed up to _Secrets Store B_, you should run `zenml secret backup --delete-secrets` instead.
4. Re-configure the ZenML server to use _Secrets Store B_ as the primary Secrets Store and remove _Secrets Store A_ as the secondary Secrets Store.
5. Re-deploy the ZenML server.

This migration strategy is not necessary if the actual location of the secrets values in the Secrets Store back-end does not change. For example:

* updating the credentials used to authenticate with the Secrets Store back-end before or after they expire
* switching to a different authentication method to authenticate with the same Secrets Store back-end (e.g. switching from an IAM account secret key to an IAM role in the AWS Secrets Manager)

If you are a [ZenML Pro](https://zenml.io/pro) user, you can configure your cloud backend based on your [deployment scenario](../system-architectures.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
