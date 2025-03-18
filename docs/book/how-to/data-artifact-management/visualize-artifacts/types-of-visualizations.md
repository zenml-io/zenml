---
description: Types of visualizations in ZenML.
---

# Types of visualizations

ZenML automatically saves visualizations of many common data types and allows you to view these visualizations in the ZenML dashboard:

![ZenML Artifact Visualizations](../../../.gitbook/assets/artifact_visualization_dashboard.png)

Alternatively, any of these visualizations can also be displayed in Jupyter notebooks using the `artifact.visualize()` method:

![output.visualize() Output](../../../.gitbook/assets/artifact_visualization_evidently.png)

Some examples of default visualizations are:

- A statistical representation of a [Pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) Dataframe represented as a png image.
- Drift detection reports by [Evidently](https://docs.zenml.io/stacks/data-validators/evidently), [Great Expectations](https://docs.zenml.io/stacks/data-validators/great-expectations), and [whylogs](https://docs.zenml.io/stacks/data-validators/whylogs).
- A [Hugging Face](https://zenml.io/integrations/huggingface) datasets viewer embedded as a HTML iframe.

![output.visualize() output for the Hugging Face datasets viewer](../../../.gitbook/assets/artifact_visualization_huggingface.gif)

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
