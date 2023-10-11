---
description: Managing of your data/features.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


Feature stores allow data teams to serve data via an offline store, and an 
online low-latency store where data is kept in sync between the two. It also 
offers a centralized registry where features (and feature schemas) are stored 
for use within a team or wider organization.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the feature stores, which 
will be available soon. As a result, their extension is not possible at the 
moment. If you would like to use a feature store in your stack, please check 
the list of already available feature stores down below.
{% endhint %}

## List of available feature stores

For production use cases, some more flavors can be found in specific 
`integrations` modules. In terms of features stores, ZenML features an 
integration of `feast`.

|                                                                                                                                                           | Flavor | Integration |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------------|
| [FeastFeatureStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.feast.feature_stores.feast_feature_store.FeastFeatureStore) | feast  | feast       |

If you would like to see the available flavors for feature stores, you can 
use the command:

```shell
zenml feature-store flavor list
```