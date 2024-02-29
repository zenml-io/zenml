---
description: Managing data in feature stores.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Feature Stores

Feature stores allow data teams to serve data via an offline store and an online low-latency store where data is kept in
sync between the two. It also offers a centralized registry where features (and feature schemas) are stored for use
within a team or wider organization.

As a data scientist working on training your model, your requirements for how you access your batch / 'offline' data
will almost certainly be different from how you access that data as part of a real-time or online inference setting.
Feast solves the problem of developing [train-serve skew](https://ploomber.io/blog/train-serve-skew/) where those two
sources of data diverge from each other.

Feature stores are a relatively recent addition to commonly-used machine learning stacks.

### When to use it

The feature store is an optional stack component in the ZenML Stack. The feature store as a technology should be used to
store the features and inject them into the process on the server side. This includes

* Productionalize new features
* Reuse existing features across multiple pipelines and models
* Achieve consistency between training and serving data (Training Serving Skew)
* Provide a central registry of features and feature schemas

### List of available feature stores

For production use cases, some more flavors can be found in specific `integrations` modules. In terms of features
stores, ZenML features an integration of `feast`.

| Feature Store                      | Flavor   | Integration | Notes                                                                    |
|------------------------------------|----------|-------------|--------------------------------------------------------------------------|
| [FeastFeatureStore](feast.md)      | `feast`  | `feast`     | Connect ZenML with already existing Feast                                |
| [Custom Implementation](custom.md) | _custom_ |             | Extend the feature store abstraction and provide your own implementation |

If you would like to see the available flavors for feature stores, you can use the command:

```shell
zenml feature-store flavor list
```

### How to use it

The available implementation of the feature store is built on top of the feast integration, which means that using a
feature store is no different from what's described on the [feast page: How to use it?](feast.md#how-do-you-use-it).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
