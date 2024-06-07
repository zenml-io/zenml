# Connect in with your User (interactive)

You can authenticate your clients with the ZenML Server using the ZenML CLI and the web based login. This can be executed with the command:

```bash
zenml connect --url https://...
```

This command will start a series of steps to validate the device from where you are connecting that will happen in your browser. You can choose whether to mark your respective device as trusted or not. If you choose not to click `Trust this device`, a 24-hour token will be issued for authentication services. Choosing to trust the device will issue a 30-day token instead.

To see all devices you've permitted, use the following command:

```bash
zenml authorized-device list
```

Additionally, the following command allows you to more precisely inspect one of these devices:

```bash
zenml authorized-device describe <DEVICE_ID>  
```

For increased security, you can invalidate a token using the `zenml device lock` command followed by the device ID. This helps provide an extra layer of security and control over your devices.

```
zenml authorized-device lock <DEVICE_ID>  
```

To keep things simple, we can summarize the steps:

1. Use the `zenml connect --url` command to start a device flow and connect to a zenml server.
2. Choose whether to trust the device when prompted.
3. Check permitted devices with `zenml devices list`.
4. Invalidate a token with `zenml device lock ...`.

### Important notice

Using the ZenML CLI is a secure and comfortable way to interact with your ZenML tenants. It's important to always ensure that only trusted devices are used to maintain security and privacy.

Don't forget to manage your device trust levels regularly for optimal security. Should you feel a device trust needs to be revoked, lock the device immediately. Every token issued is a potential gateway to access your data, secrets and infrastructure.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


