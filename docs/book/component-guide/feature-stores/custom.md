---
description: Learning how to develop a custom feature store.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Develop a Custom Feature Store

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

Feature stores allow data teams to serve data via an offline store, and an online low-latency store where data is kept in sync between the two. It also offers a centralized registry where features (and feature schemas) are stored for use within a team or wider organization.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the feature stores, which will be available soon. As a result, their extension is not possible at the moment. If you would like to use a feature store in your stack, please check the list of already available feature stores down below.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
