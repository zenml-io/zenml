---
description: Use Jupyter Notebooks to run remote steps or pipelines
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 📔 Run remote pipelines from notebooks

ZenML steps and pipelines can be defined in a Jupyter notebook and executed remotely. To do so, ZenML will extract the code from your notebook cells and run them as Python modules inside the Docker containers that execute your pipeline steps remotely. For this to work, the notebook cells in which you define your steps need to meet certain conditions.

Learn more about it in the following sections:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Define steps in notebook cells</td><td></td><td></td><td><a href="define-steps-in-notebook-cells.md">define-steps-in-notebook-cells.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
