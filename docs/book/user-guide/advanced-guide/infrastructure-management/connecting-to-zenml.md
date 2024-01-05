---
description: Various means of connecting to ZenML.
---

# Connecting to ZenML

Once [ZenML is deployed](../../production-guide/deploying-zenml.md), there are various means to connect to it:

## Using the ZenML CLI to connect to a deployed ZenML Server

You can authenticate your clients with the ZenML Server using the ZenML CLI and the web based login. This
can be executed with the command:

```bash
zenml connect --url https://...
```

This command will start a series of steps to validate the device from where you are connecting that will happen in your browser. You can choose whether to
mark your respective device as trusted or not. If you choose not to
click `Trust this device`, a 24-hour token will be issued for authentication
services. Choosing to trust the device will issue a 30-day token instead.

To see all devices you've permitted, use the following command:

```bash
zenml authorized-device list
```

Additionally, the following command allows you to more precisely inspect one of
these devices:

```bash
zenml authorized-device describe <DEVICE_ID>  
```

For increased security, you can invalidate a token using the `zenml device lock`
command followed by the device ID. This helps provide an extra layer of security
and control over your devices.

```
zenml authorized-device lock <DEVICE_ID>  
```

To keep things simple, we can summarize the steps:

1. Use the `zenml connect --url` command to start a device flow and connect to a
   zenml server.
2. Choose whether to trust the device when prompted.
3. Check permitted devices with `zenml devices list`.
4. Invalidate a token with `zenml device lock ...`.


### Important notice

Using the ZenML CLI is a secure and comfortable way to interact with your ZenML
tenants. It's important to always ensure that only trusted devices are used to
maintain security and privacy.

Don't forget to manage your device trust levels regularly for optimal security.
Should you feel a device trust needs to be revoked, lock the device immediately.
Every token issued is a potential gateway to access your data, secrets and
infrastructure.

## Using Service Accounts to connect to a deployed ZenML Server

Sometimes you may need to authenticate to a ZenML server from an non-interactive
environment where the web login is not possible, like a CI/CD workload or a
serverless function. In these cases, you can configure a service account and an
API key and use the API key to authenticate to the ZenML server:

```bash
zenml service-account create --name <SERVICE_ACCOUNT_NAME>
```

This command creates a service account and an API key for it. The API key is
displayed as part of the command output and cannot be retrieved later. You can
then use the issued API key to connect your ZenML client to the server through
one of the following methods:

* using the CLI:

```bash
zenml connect --url https://... --api-key <API_KEY>
```

* setting the `ZENML_STORE_URL` and `ZENML_STORE_API_KEY` environment
variables when you set up your ZenML client for the first time. This method
is particularly useful when you are using the ZenML client in an automated CI/CD
workload environment like GitHub Actions or GitLab CI or in a containerized
environment like Docker or Kubernetes:

```bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
```

To see all the service accounts you've created and their API keys, use the
following commands:

```bash
zenml service-account list
zenml service-account api-key <SERVICE_ACCOUNT_NAME> list
```

Additionally, the following command allows you to more precisely inspect one of
these service accounts and an API key:

```bash
zenml service-account describe <SERVICE_ACCOUNT_NAME>
zenml service-account api-key <SERVICE_ACCOUNT_NAME> describe <API_KEY_NAME>
```

API keys don't have an expiration date. For increased security, we recommend
that you regularly rotate the API keys to prevent unauthorized access to your
ZenML server. You can do this with the ZenML CLI:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME>
```

Running this command will create a new API key and invalidate the old one. The
new API key is displayed as part of the command output and cannot be retrieved
later. You can then use the new API key to connect your ZenML client to the
server just as described above.

When rotating an API key, you can also configure a retention period for the old
API key. This is useful if you need to keep the old API key for a while to
ensure that all your workloads have been updated to use the new API key. You can
do this with the `--retain` flag. For example, to rotate an API key and keep the
old one for 60 minutes, you can run the following command:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME> \
      --retain 60
```

For increased security, you can deactivate a service account or an API key using
one of the following commands:

```
zenml service-account update <SERVICE_ACCOUNT_NAME> --active false
zenml service-account api-key <SERVICE_ACCOUNT_NAME> update <API_KEY_NAME> \
      --active false
```

Deactivating a service account or an API key will prevent it from being used to
authenticate and has immediate effect on all workloads that use it.

To keep things simple, we can summarize the steps:

1. Use the `zenml service-account create` command to create a service account
   and an API key.
2. Use the `zenml connect --url <url> --api-key <api-key>` command to connect
   your ZenML client to the server using the API key.
3. Check configured service accounts with `zenml service-account list`.
4. Check configured API keys with `zenml service-account api-key <SERVICE_ACCOUNT_NAME> list`.
5. Regularly rotate API keys with `zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate`.
6. Deactivate service accounts or API keys with `zenml service-account update` or `zenml service-account api-key <SERVICE_ACCOUNT_NAME> update`.


### Important notice

Every API key issued is a potential gateway to access your data, secrets and
infrastructure. It's important to regularly rotate API keys and deactivate
or delete service accounts and API keys that are no longer needed.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>