---
description: Collaborating with the ZenML community.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Leverage community-contributed plugins

The ZenML Hub is a central platform that enables our users to search, share and discover community-contributed code, such as flavors, materializers, and steps, that can be used across organizations. The goal is to allow our users to extend their ZenML experience by leveraging the community's diverse range of implementations.

{% hint style="info" %}
If you're interested in learning more about our motivation for implementing the ZenML Hub and our plans for its future, we invite you to read [our new blog post](https://blog.zenml.io/zenml-hub-launch). In addition to this technical documentation, the blog post provides a comprehensive overview of the ZenML Hub's goals and objectives, as well as the features that we plan to introduce in the future.
{% endhint %}

### Plugins <a href="#plugins" id="plugins"></a>

The ZenML Hub revolves around the concept of **plugins**, which can be made up of one or multiple ZenML entities, including flavors, materializers, and steps. Aside from the implementation of these entities, every plugin in the hub is also equipped with:

* a **`README.md`** file that provides documentation
* a logo that appears on the hub/dashboard
* a list of requirements necessary for running the plugin
* optionally, a code example that demonstrates its usage.

Users can create a ZenML Hub account to contribute, rate, and star these plugins. To ensure uniqueness and versioning, each submitted plugin is named after the user who created it and is automatically versioned. Plugins authored or approved by the ZenML core developers will have a "verified" badge, as well as a stability/maturity rating.

### What is already built-in? <a href="#what-is-already-built-in" id="what-is-already-built-in"></a>

With the release of ZenML version 0.38.0, the ZenML Hub will make its first appearance and be equipped with a set of plugins that feature ZenML-verified steps (with a heavy-emphasis on data loader steps). In future iterations, the ZenML team is actively working on expanding the Hub's capabilities and plans to introduce additional entities, such as materializers and flavors.

## How do I use it?

If you come across a plugin in the ZenML Hub that you find useful or interesting, installing it is a straightforward process. Using our CLI, you can quickly install it via:

```bash
zenml hub install <PLUGIN_NAME>
```

Once installed, the entities in the plugin can be imported like any other library in your Python code and used alongside your existing code.

```python
from zenml.hub.plugin1 import step_from_hub
from zenml import pipeline

@pipeline
def my_pipeline():
    step_from_hub(...)

my_pipeline()
```

Additionally, if you want to customize or iterate on a plugin, you can clone the plugin repository and make changes to it as needed. This enables you to customize the plugin to better suit your specific use case, or contribute back to the community by improving upon the plugin's functionality.

```bash
zenml hub clone <PLUGIN_NAME>
```

## How do I see available plugins?

{% tabs %}
{% tab title="Dashboard" %}
You can see the available plugins on the `Plugins` page:

![Dashboard List Plugin](../../.gitbook/assets/plugins\_dashboard.png)

You can browse through the plugins to see more details.
{% endtab %}

{% tab title="CLI" %}
You can see the available plugins via the CLI:

```bash
zenml hub list
```

You should see a table similar to:

![CLI List Plugin](../../.gitbook/assets/plugins\_cli.png)
{% endtab %}
{% endtabs %}

## How do I create my own plugin?

In order to create your own plugin and submit it to the ZenML hub, you need to first log in. In the first version, authentication is only possible through GitHub.

{% hint style="info" %}
If you haven't used the ZenML Hub before, this process will create a ZenML Hub account that shares the same username as your GitHub account. It will also associate your current ZenML user with this newly generated ZenML Hub account.
{% endhint %}

{% tabs %}
{% tab title="Dashboard" %}
In order to log in through the dashboard, you can use the connect button on the Plugins page.

![Dashboard Login](../../.gitbook/assets/login\_dashboard.png)

Similar to the CLI, you can disconnect your account using the Disconnect button.
{% endtab %}

{% tab title="CLI" %}
In order to log in through the CLI:

```bash
zenml hub login
```

This will open up a page where you can log in to your GitHub account and copy over the generated token to your CLI.

In order to log out, you can do:

```bash
zenml hub logout
```
{% endtab %}
{% endtabs %}

After logging in, you can start submitting your own plugins. The submitted plugins need to follow a set of standards which are described as guidelines in [our template repository](https://github.com/zenml-io/zenml-hub-plugin-template).

{% tabs %}
{% tab title="Dashboard" %}
If you are submitting your plugin through the dashboard, you need to provide the required metadata about your plugin.

![Dashboard Create Plugin](../../.gitbook/assets/create\_plugin\_dashboard.png)
{% endtab %}

{% tab title="CLI" %}
If you are submitting your plugin through the CLI, you can use the interactive mode to provide the details regarding your plugin:

```bash
zenml hub submit -i
```
{% endtab %}
{% endtabs %}

Once submitted, a wheel will be created and stored based on your plugin. This process might take some time before the plugin is ready to install and use. You can check the status of this process by inspecting the status of the plugin.

## ZenML Hub service status

The status of the ZenML Hub service is being tracked live in [the ZenML status page](https://zenml.statuspage.io/). You can subscribe there to receive notifications about scheduled maintenance windows, unplanned downtime events and more.

<figure><img src="../../.gitbook/assets/statuspage.png" alt=""><figcaption><p>The ZenML public services status page</p></figcaption></figure>
