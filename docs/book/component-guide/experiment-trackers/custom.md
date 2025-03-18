---
description: Learning how to develop a custom experiment tracker.
---

# Develop a custom experiment tracker

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the Experiment Tracker, which will be available soon. As a result, their extension is not recommended at the moment. When you are selecting an Experiment Tracker for your stack, you can use one of [the existing flavors](./#experiment-tracker-flavors).

If you need to implement your own Experiment Tracker flavor, you can still do so, but keep in mind that you may have to refactor it when the base abstraction is released.
{% endhint %}

### Build your own custom experiment tracker

If you want to create your own custom flavor for an experiment tracker, you can follow the following steps:

1. Create a class that inherits from the `BaseExperimentTracker` class and implements the abstract methods.
2. If you need any configuration, create a class that inherits from the `BaseExperimentTrackerConfig` class and add your configuration parameters.
3. Bring both the implementation and the configuration together by inheriting from the `BaseExperimentTrackerFlavor` class.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml experiment-tracker flavor register <path.to.MyExperimentTrackerFlavor>
```

For example, if your flavor class `MyExperimentTrackerFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml experiment-tracker flavor register flavors.my_flavor.MyExperimentTrackerFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](https://docs.zenml.io/how-to/infrastructure-deployment/infrastructure-as-code/best-practices) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml experiment-tracker flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomExperimentTrackerFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomExperimentTrackerConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomExperimentTracker** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomExperimentTrackerFlavor` and the `CustomExperimentTrackerConfig` are implemented in a different module/path than the actual `CustomExperimentTracker`).
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
