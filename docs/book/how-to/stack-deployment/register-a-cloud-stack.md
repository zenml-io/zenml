---
description: Register a cloud stack easily
---

# Register a cloud stack with existing infrastructure

In ZenML, the [stack](../../user-guide/production-guide/understand-stacks.md) 
is a fundamental concept that represents the configuration of your 
infrastructure. In a normal workflow, creating a stack requires you to first 
deploy the necessary pieces of infrastructure and then define them as stack 
components in ZenML with proper authentication.

Especially in a remote setting, this process can be challenging and 
time-consuming, and it may create multi-faceted problems. This is why we 
implemented a feature called the stack wizard, that allows you to **browse 
through your existing infrastructure and use it to register a ZenML cloud 
stack**.

{% hint style="info" %}
If you do not have the required infrastructure pieces already deployed
on your cloud, you can also use [the 1-click deployment tool to build your 
cloud stack](deploy-a-cloud-stack.md).
{% endhint %}

# How to use the Stack Wizard?

At the moment, the stack wizard can only be accessed through our CLI:

{% tabs %}
{% tab title="CLI" %}

In order to register a remote stack over the CLI with the stack wizard,
you can use the following command:

```shell
zenml stack register <STACK_NAME> -p aws
```

{% hint style="warning" %}
Currently, the stack wizard only works on AWS. We are working on bringing 
support to GCP and Azure as well. Stay in touch for further updates.
{% endhint %}

### AWS



{% endtab %}

{% tab title="Dashboard" %}

We are working hard to bring this feature to our dashboard as well. Stay in 
touch for further updates.

{% endtab %}
{% endtabs %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
