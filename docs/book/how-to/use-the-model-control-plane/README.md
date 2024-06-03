# 🪆 Use the Model Control Plane

![Walkthrough of ZenML Model Control Plane (Dashboard available only on ZenML Cloud)](../../.gitbook/assets/mcp_walkthrough.gif)

A `Model` is simply an entity that groups pipelines, artifacts, metadata, and other crucial business data into a unified entity. A ZenML Model is a concept that more broadly encapsulates your ML products business logic. You may even think of a ZenML Model as a "project" or a "workspace"

{% hint style="warning" %}
Please note that one of the most common artifacts that is associated with a Model in ZenML is the so-called technical model, which is the actually model file/files that holds the weight and parameters of a machine learning training result. However, this is not the only artifact that is relevant; artifacts such as the training data and the predictions this model produces in production are also linked inside a ZenML Model.
{% endhint %}

Models are first-class citizens in ZenML and as such viewing and using them is unified and centralized in the ZenML API, client as well as on the [ZenML Cloud](https://zenml.io/cloud) dashboard.

A Model captures lineage information and more. Within a Model, different Model versions can be staged. For example, you can rely on your predictions at a specific stage, like `Production`, and decide whether the Model version should be promoted based on your business rules during training. Plus, accessing data from other Models and their versions is just as simple.

The Model Control Plane is how you manage your models through this unified interface. It allows you to combine the logic of your pipelines, artifacts and crucial business data along with the actual 'technical model'.

To see an end-to-end example, please refer to the [starter guide](../../user-guide/starter-guide/track-ml-models.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
