---
description: How to annotate your data
---

Annotators are a stack component that enables the use of data annotation as part
of your ZenML stack and pipelines. You can use the associated CLI command to
launch annotation, configure your datasets and get stats on how many labeled
tasks you have ready for use.

As a data scientist working on training your model, your requirements for how
you access your batch / 'offline' data
will almost certainly be different from how you access that data as part of a
real-time or online inference setting.
Feast solves the problem of
developing [train-serve skew](https://ploomber.io/blog/train-serve-skew/) where
those two
sources of data diverge from each other.

Feature stores are a relatively recent addition to commonly-used machine
learning stacks. 

## When to use it

The feature store is an optional stack component in the ZenML Stack.
The feature store as a technology should be used to store the features and
inject them into the process in the server-side. This includes 

* Productionalize new features
* Reuse existing features across multiple pipelines and models
* Achieve consistency between training and serving data (Training Serving Skew)
* Provide a central registry of features and feature schemas

## List of available feature stores

For production use cases, some more flavors can be found in specific 
`integrations` modules. In terms of features stores, ZenML features an 
integration of `feast`.

| Feature Store | Flavor | Integration | Notes             |
|----------------|--------|-------------|-------------------|
| [FeastFeatureStore](./feast.md) | `feast` | `feast` | Connect ZenML with already existing Feast |
| [Custom Implementation](./custom.md) | _custom_ | | Extend the feature store abstraction and provide your own implementation |

If you would like to see the available flavors for feature stores, you can 
use the command:

```shell
zenml feature-store flavor list
```

## How to use it

The available implementation of the feature store is built on top of the feast integration,
which means that using a feature store is no different than what's described in the [feast page: How to use it?](./feast.md#how-to-use-it).
