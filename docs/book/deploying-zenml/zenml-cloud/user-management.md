# User Management

### Organizations, Tenants, and Roles

ZenML Cloud arranges various aspects of your work experience around the concept
of an **Organization.** This is the topmost level structure within the ZenML
Cloud environment. Generally, an organization contains a group of users and one
or more tenants, which are individual, isolated deployments of the ZenML server.

Every user in an organization has a distinct role. Each role configures what
they can view, modify, and their level of involvement in collaborative tasks. A
role thus helps determine the level of access that a user has within an
organization.

The `admin` has all permissions on an organization. They are allowed to add
members, adjust the billing information and assign roles. The `editor` can still
fully manage tenants and members but is not allowed to access the subscription
information or delete the organization. The `viewer` Role allows you to allow
users to access the tenants within the organization with no real permissions in
the Cloud Control Plane.&#x20;

### Inviting Team Members

Inviting users to your organization to work on the organization's tenants is
easy. Simply click `Add Member` in the Organization settings, and give them an
initial Role. The User will be sent an invitation email. If a user is part of an
organization, they can utilize their login on all tenants they have authority to
access.

### Using the ZenML CLI to connect to a Tenant

ZenML Cloud uses the Command Line Interface (CLI) to connect to a tenant. This
can be executed with the command:

```bash
zenml connect --url https://...
```

This command will initiate a browser device flow. Users can choose whether to
mark their respective device as trusted or not. If you choose not to
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
   tenant.
2. Choose whether to trust the device when prompted.
3. Check permitted devices with `zenml devices list`.
4. Invalidate a token with `zenml device lock ...`.

#### Please remember:

Using the ZenML CLI is a secure and comfortable way to interact with your zenml
tenants. It's important to always ensure that only trusted devices are used to
maintain security and privacy.

Don't forget to manage your device trust levels regularly for optimal security.
Should you feel a device trust needs to be revoked, lock the device immediately.
Every token issued is a potential gateway to access your data, secrets and
infrastructure.

### Device-to-device authentication

{% hint style="info" %}
We are actively developing low privilege service accounts and will update this
when they are implemented. For the time being all workloads (like for example a
pipeline run) will get an irrevocable API Token that is valid for 24h - please
reach out to us in case longer-lasting tokens are needed for your Tenants.
{% endhint %}