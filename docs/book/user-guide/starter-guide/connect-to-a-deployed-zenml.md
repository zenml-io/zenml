---
description: Learning about the ZenML server.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Connect to a deployed ZenML

Although the basic functionalities of ZenML work perfectly on your local machine, you need to connect to **a deployed ZenML server** to use remote services and infrastructure.

### ZenML Server

When you first get started with ZenML, it is based on the following architecture on your machine.

![Scenario 1: ZenML default local configuration](../../.gitbook/assets/Scenario1.png)

The SQLite database that you can see in this diagram is used to store information about pipelines, pipeline runs, stacks, and other configurations. In the previous pages, we used the `zenml up` command to spin up a local rest server to serve the dashboard as well. The diagram for this will look as follows:

![Scenario 2: ZenML with a local REST Server](../../.gitbook/assets/Scenario2.png)

In order to move into production, you will need to deploy this server somewhere centrally so that the different cloud stack components can read from and write to the server. Additionally, this also allows all your team members to connect to it and share stacks and pipelines.

![Scenario 3: Deployed ZenML Server](../../.gitbook/assets/Scenario3.png)

#### Connect your client to the server

When ZenML is deployed, the client can be explicitly connected. This is how you do it:

```bash
zenml connect --url https://<your-own-deployment> --username default
```

You will be prompted for your password:

```bash
Connecting to: 'https://<your-own-deployment>'...
Password for user zenml (press ENTER for empty password) []:
```

{% hint style="info" %}
In Scenario 2, the `zenml up` command implicitly connects the client to the server.
{% endhint %}

{% hint style="warning" %}
In order to use the `zenml connect` command, you need to first deploy a remote ZenML server. If you are the person who is setting up it for your organization and looking for detailed documentation regarding the deployment, head on over to the [Platform Guide](../../platform-guide/set-up-your-mlops-platform/set-up-your-mlops-platform.md) to set it up on your infrastructure of choice.

Alternatively, if you are just getting started and want to try things out along with this starter guide, take a look at the [MLOps Platform Sandbox](switch-to-production.md), which allows you to spin up a remote sandbox ZenML deployment.
{% endhint %}

And just like that, your client should be connected to the server. You can verify this by running `zenml status`:

```bash
Using configuration from: '/home/apenner/.config/zenml'
Local store files are located at: '/home/apenner/.config/zenml/local_stores'
Connected to a ZenML server: '<your-own-deployment>'
The current user is: 'zenml'
The active workspace is: 'default' (global)
The active stack is: 'default' (global)
```

Similar to the local case, you can now run `zenml show` to open the dashboard of the server that you are currently connected to.

Finally, if you would like to **disconnect** from the current ZenML server and revert to using the local default database, simply run `zenml disconnect`.
