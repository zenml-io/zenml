---
description: >-
  Connect to the ZenML server using the ZenML CLI and the web based login.
---

# Connect in with your User (interactive)

You can authenticate your clients with the ZenML Server using the ZenML CLI and the web‑based login (device flow). This method is ideal for humans working locally and applies to OSS servers and ZenML Pro workspaces.

```bash
zenml login https://...
```

This command starts a browser flow to validate the device you are connecting from. You can choose whether to mark the device as trusted. If you don’t trust the device, a 24‑hour token is issued; if you do, a 30‑day token is issued.

{% hint style="warning" %}
Managing authorized devices for ZenML Pro workspaces is not yet supported in the dashboard. CLI device management is available.
{% endhint %}

To see all devices you've permitted, use the following command:

```bash
zenml authorized-device list
```

Additionally, the following command allows you to more precisely inspect one of these devices:

```bash
zenml authorized-device describe <DEVICE_ID>  
```

For increased security, you can invalidate a token using the `zenml authorized-device lock` command followed by the device ID.

```
zenml authorized-device lock <DEVICE_ID>  
```

To keep things simple, we can summarize the steps:

1. Use the `zenml login <URL>` command to start a device flow and connect to a zenml server.
2. Choose whether to trust the device when prompted.
3. Check permitted devices with `zenml authorized-device list`.
4. Invalidate a token with `zenml authorized-device lock ...`.

### Important notice

Using the ZenML CLI is a secure and comfortable way to interact with your ZenML servers. It's important to always ensure that only trusted devices are used to maintain security and privacy.

{% hint style="info" %}
Calling the ZenML Pro management API (`cloudapi.zenml.io`)? Interactive CLI login does not apply there. Use a ZenML Pro Personal Access Token or a ZenML Pro Service Account and API key instead. See [ZenML Pro API Getting Started](https://docs.zenml.io/api-reference/pro-api/getting-started).
{% endhint %}

Don't forget to manage your device trust levels regularly for optimal security. Should you feel a device trust needs to be revoked, lock the device immediately. Every token issued is a potential gateway to access your data, secrets and infrastructure.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


