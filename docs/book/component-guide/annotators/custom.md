---
description: Learning how to develop a custom annotator.
---

# Develop a Custom Annotator

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

Annotators are a stack component that enables the use of data annotation as part of your ZenML stack and pipelines. You can use the associated CLI command to launch annotation, configure your datasets and get stats on how many labeled tasks you have ready for use.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the annotators, which will be available soon. As a result, their extension is not possible at the moment. If you would like to use an annotator in your stack, please check the list of already available feature stores down below.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
