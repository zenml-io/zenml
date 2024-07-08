---
description: Register a cloud stack easily
---

# Register a cloud stack with existing infrastructure

In ZenML, the [stack]() is a fundamental concept that represents the 
configuration of your infrastructure. In a normal workflow, creating a stack
requires you to first deploy the necessary pieces of infrastructure and then 
define them as stack components in ZenML with proper authentication.

Especially in a remote setting, this process can sometimes be challenging and 
time-consuming, and it may create a multi-faceted problem. This is why we 
implemented a feature called the stack wizard, that allows you to **browse 
through your existing infrastructure and use it to register a ZenML cloud 
stack**.

{% hint style="info" %}
If you do not have the required infrastructure pieces already deployed
on your cloud, you can also use the 1-click deployment tool to build your 
cloud stack.
{% endhint %}

# How to use the Stack Wizard

The stack wizard can only be accessed through the CLI:

{% tabs %}
{% tab title="CLI" %}

In order to create a remote stack over the CLI you can use the following 
command:

```shell
zenml stack register <STACK_NAME> -p aws
```

### AWS

{% hint style="warning" %}
Currently, the stack wizard only works on AWS. We are working on supporting 
GCP and Azure as well. Stay in touch for further updates.
{% endhint %}

{% endtab %}
{% tab title="Dashboard" %}

We are working hard to bring this feature to our dashboard as well. Stay in 
touch for further updates.

{% endtab %}
{% endtabs %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
