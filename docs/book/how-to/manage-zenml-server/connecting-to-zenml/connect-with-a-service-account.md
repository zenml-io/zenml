---
description: >-
  Connect to the ZenML server using a service account and an API key.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Connect with a Service Account

{% hint style="warning" %}
**Workspace-level service accounts are not available in ZenML Pro**

If you are using ZenML Pro, you will notice that workspace-level service accounts are not available. Please use [organization level service accounts instead](https://docs.zenml.io/pro/access-management/service-accounts).
{% endhint %}

Sometimes you may need to authenticate to a ZenML server from a non-interactive environment where the web login is not possible, like a CI/CD workload or a serverless function. In these cases, you can configure a service account and an API key and use the API key to authenticate to the ZenML server:

```bash
zenml service-account create <SERVICE_ACCOUNT_NAME>
```

This command creates a service account and an API key for it. The API key is displayed as part of the command output and cannot be retrieved later. You can then use the issued API key to connect your ZenML client to the server through one of the following methods:

* using the CLI:

```bash
# This command will prompt you to enter the API key
zenml login https://... --api-key
```

* setting the `ZENML_STORE_URL` and `ZENML_STORE_API_KEY` environment variables when you set up your ZenML client for the first time. This method is particularly useful when you are using the ZenML client in an automated CI/CD workload environment like GitHub Actions or GitLab CI or in a containerized environment like Docker or Kubernetes:

```bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
```

{% hint style="info" %}
You don't need to run `zenml login` after setting these two environment
variables and can start interacting with your server right away.
{% endhint %}

{% hint style="info" %}
Using ZenML Pro?

Use an organization‑level service account and API key. Set the workspace URL and your org service account API key as environment variables:

```bash
export ZENML_STORE_URL=https://<your-workspace>.zenml.io
export ZENML_STORE_API_KEY=<YOUR_ORG_SERVICE_ACCOUNT_API_KEY>
# Optional for self-hosted Pro deployments:
export ZENML_PRO_API_URL=https://<your-pro-api-url>
```

You can also authenticate via CLI:

```bash
zenml login <your-workspace-name> --api-key
# You will be prompted to enter your organization service account API key
```
{% endhint %}

To see all the service accounts you've created and their API keys, use the following commands:

```bash
zenml service-account list
zenml service-account api-key <SERVICE_ACCOUNT_NAME> list
```

Additionally, the following command allows you to more precisely inspect one of these service accounts and an API key:

```bash
zenml service-account describe <SERVICE_ACCOUNT_NAME>
zenml service-account api-key <SERVICE_ACCOUNT_NAME> describe <API_KEY_NAME>
```

API keys don't have an expiration date. For increased security, we recommend that you regularly rotate the API keys to prevent unauthorized access to your ZenML server. You can do this with the ZenML CLI:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME>
```

Running this command will create a new API key and invalidate the old one. The new API key is displayed as part of the command output and cannot be retrieved later. You can then use the new API key to connect your ZenML client to the server just as described above.

When rotating an API key, you can also configure a retention period for the old API key. This is useful if you need to keep the old API key for a while to ensure that all your workloads have been updated to use the new API key. You can do this with the `--retain` flag. For example, to rotate an API key and keep the old one for 60 minutes, you can run the following command:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME> \
      --retain 60
```

For increased security, you can deactivate a service account or an API key using one of the following commands:

```
zenml service-account update <SERVICE_ACCOUNT_NAME> --active false
zenml service-account api-key <SERVICE_ACCOUNT_NAME> update <API_KEY_NAME> \
      --active false
```

Deactivating a service account or an API key will prevent it from being used to authenticate and has immediate effect on all workloads that use it.

To keep things simple, we can summarize the steps:

1. Use the `zenml service-account create` command to create a service account and an API key.
2. Use the `zenml login <url> --api-key` command to connect your ZenML client to the server using the API key.
3. Check configured service accounts with `zenml service-account list`.
4. Check configured API keys with `zenml service-account api-key <SERVICE_ACCOUNT_NAME> list`.
5. Regularly rotate API keys with `zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate`.
6. Deactivate service accounts or API keys with `zenml service-account update` or `zenml service-account api-key <SERVICE_ACCOUNT_NAME> update`.

## Programmatic access with API keys

You can use a service account's API key to access the ZenML server's REST API programmatically. This is particularly useful when you need to make long-term securely authenticated HTTP requests to the ZenML API endpoints. This is the recommended way to access the ZenML API programmatically when you're not using the ZenML CLI or Python client.

Accessing the API with this method is thoroughly documented in the [API reference section](https://docs.zenml.io/api-reference/oss-api/getting-started#using-a-service-account-and-an-api-key).

{% hint style="warning" %}
The service accounts described here are only supported for OSS servers. If you are trying to access a ZenML Pro Workspace API programmatically, use a Pro API service account instead. See [Pro API Getting Started](https://docs.zenml.io/api-reference/pro-api/getting-started).
{% endhint %}

## Important notice

Every API key issued is a potential gateway to access your data, secrets and infrastructure. It's important to regularly rotate API keys and deactivate or delete service accounts and API keys that are no longer needed.
