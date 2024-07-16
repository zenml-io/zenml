---
description: Types of visualizations in ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Types of visualizations

ZenML automatically saves visualizations of many common data types and allows you to view these visualizations in the ZenML dashboard:

![ZenML Artifact Visualizations](../../.gitbook/assets/artifact_visualization_dashboard.png)

Alternatively, any of these visualizations can also be displayed in Jupyter notebooks using the `artifact.visualize()` method:

![output.visualize() Output](../../.gitbook/assets/artifact_visualization_evidently.png)

Currently, the following visualization types are supported:

* **HTML:** Embedded HTML visualizations such as data validation reports,
* **Image:** Visualizations of image data such as Pillow images or certain numeric numpy arrays,
* **CSV:** Tables, such as the pandas DataFrame `.describe()` output,
* **Markdown:** Markdown strings or pages.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>