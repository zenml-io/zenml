---
description: Learning about the ZenML server
---

# Connect to a deployed ZenML

Although the basic functionalities of ZenML work perfectly on your local machine, you need to connect to a deployed ZenML server to use remote services and infrastructure.

If you are the one setting up ZenML for your organization, head on over to the [Platform Guide](../../platform-guide/set-up-your-mlops-platform/) to set this up on your infrastructure of choice. Alternatively, if you are just getting started and want to try things out, the ZenML Sandbox is the right resource for you.

### Why deploy

There are three scenarios&#x20;

{% tabs %}
{% tab title="Default" %}
By default the ZenML client simply directly connects to it its local database.&#x20;

<figure><img src="../../.gitbook/assets/Scenario1.png" alt=""><figcaption><p>ZenML default local configuration</p></figcaption></figure>
{% endtab %}

{% tab title="Local Server" %}


<figure><img src="../../.gitbook/assets/Scenario2.png" alt=""><figcaption></figcaption></figure>
{% endtab %}

{% tab title="Remote Server" %}
<figure><img src="../../.gitbook/assets/Scenario3.png" alt=""><figcaption></figcaption></figure>
{% endtab %}
{% endtabs %}

