---
icon: expand
description: Annotating the data in your workflow.
---

# Annotators

Annotators are a stack component that enables the use of data annotation as part of your ZenML stack and pipelines. You
can use the associated CLI command to launch annotation, configure your datasets and get stats on how many labeled tasks
you have ready for use.

Data annotation/labeling is a core part of MLOps that is frequently left out of the conversation. ZenML will
incrementally start to build features that support an iterative annotation workflow that sees the people doing
labeling (and their workflows/behaviors) as integrated parts of their ML process(es).

![When and where to annotate.](../../.gitbook/assets/annotation-when-where.png)

There are a number of different places in the ML lifecycle where this can happen:

* **At the start**: You might be starting out without any data, or with a ton of data but no clear sense of which parts
  of it are useful to your particular problem. It’s not uncommon to have a lot of data but to be lacking accurate labels
  for that data. So you can start and get great value from bootstrapping your model: label some data, train your model,
  and use your model to suggest labels allowing you to speed up your labeling, iterating on and on in this way. Labeling
  data early on in the process also helps clarify and condense down your specific rules and standards. For example, you
  might realize that you need to have specific definitions for certain concepts so that your labeling efforts are
  consistent across your team.
* **As new data comes in**: New data will likely continue to come in, and you might want to check in with the labeling
  process at regular intervals to expose yourself to this new data. (You’ll probably also want to have some kind of
  automation around detecting data or concept drift, but for certain kinds of unstructured data you probably can never
  completely abandon the instant feedback of actual contact with the raw data.)
* **Samples generated for inference**: Your model will be making predictions on real-world data being passed in. If you
  store and label this data, you’ll gain a valuable set of data that you can use to compare your labels with what the
  model was predicting, another possible way to flag drifts of various kinds. This data can then (subject to
  privacy/user consent) be used in retraining or fine-tuning your model.
* **Other ad hoc interventions**: You will probably have some kind of process to identify bad labels, or to find the
  kinds of examples that your model finds really difficult to make correct predictions. For these, and for areas where
  you have clear class imbalances, you might want to do ad hoc annotation to supplement the raw materials your model has
  to learn from.

ZenML currently offers standard steps that help you tackle the above use cases, but the stack component and abstraction
will continue to be developed to make it easier to use.

### When to use it

The annotator is an optional stack component in the ZenML Stack. We designed our abstraction to fit into the larger ML
use cases, particularly the training and deployment parts of the lifecycle.

The core parts of the annotation workflow include:

* using labels or annotations in your training steps in a seamless way
* handling the versioning of annotation data
* allow for the conversion of annotation data to and from custom formats
* handle annotator-specific tasks, for example, the generation of UI config files that Label Studio requires for the web
  annotation interface

### List of available annotators

For production use cases, some more flavors can be found in specific `integrations` modules. In terms of annotators,
ZenML features integrations with the following tools.

| Annotator                               | Flavor         | Integration    | Notes                                                                |
|-----------------------------------------|----------------|----------------|----------------------------------------------------------------------|
| [ArgillaAnnotator](argilla.md)           | `argilla`       | `argilla`       | Connect ZenML with Argilla                                             |
| [LabelStudioAnnotator](label-studio.md) | `label_studio` | `label_studio` | Connect ZenML with Label Studio                                      |
| [PigeonAnnotator](pigeon.md) | `pigeon` | `pigeon` | Connect ZenML with Pigeon. Notebook only & for image and text classification tasks.      |
| [ProdigyAnnotator](prodigy.md)           | `prodigy`       | `prodigy`       | Connect ZenML with [Prodigy](https://prodi.gy/)                                             |
| [Custom Implementation](custom.md)      | _custom_       |                | Extend the annotator abstraction and provide your own implementation |

If you would like to see the available flavors for annotators, you can use the command:

```shell
zenml annotator flavor list
```

### How to use it

The available implementation of the annotator is built on top of the Label
Studio integration, which means that using an annotator currently is no
different from what's described on the [Label Studio page: How to use
it?](label-studio.md#how-do-you-use-it). ([Pigeon](pigeon.md) is also supported, but has a
very limited functionality and only works within Jupyter notebooks.)

### A note on names

The various annotation tools have mostly standardized around the naming of key concepts as part of how they build their
tools. Unfortunately, this hasn't been completely unified so ZenML takes an opinion on which names we use for our stack
components and integrations. Key differences to note:

* Label Studio refers to the grouping of a set of annotations/tasks as a 'Project', whereas most other tools use the
  term 'Dataset', so ZenML also calls this grouping a 'Dataset'.
* The individual meta-unit for 'an annotation + the source data' is referred to in different ways, but at ZenML (and
  with Label Studio) we refer to them as 'tasks'.

The remaining core concepts ('annotation' and 'prediction', in particular) are broadly used among annotation tools.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
