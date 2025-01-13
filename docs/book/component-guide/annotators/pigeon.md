---
description: Annotating data using Pigeon.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Pigeon

Pigeon is a lightweight, open-source annotation tool designed for quick and easy labeling of data directly within Jupyter notebooks. It provides a simple and intuitive interface for annotating various types of data, including:

* Text Classification
* Image Classification
* Text Captioning

### When would you want to use it?

![Pigeon annotator interface](../../.gitbook/assets/pigeon.png)

If you need to label a small to medium-sized dataset as part of your ML workflow and prefer the convenience of doing it directly within your Jupyter notebook, Pigeon is a great choice. It is particularly useful for:

* Quick labeling tasks that don't require a full-fledged annotation platform
* Iterative labeling during the exploratory phase of your ML project
* Collaborative labeling within a Jupyter notebook environment

### How to deploy it?

To use the Pigeon annotator, you first need to install the ZenML Pigeon integration:

```shell
zenml integration install pigeon
```

Next, register the Pigeon annotator with ZenML, specifying the output directory where the annotation files will be stored:

```shell
zenml annotator register pigeon --flavor pigeon --output_dir="path/to/dir"
```

Note that the `output_dir` is relative to the repository or notebook root.

Finally, add the Pigeon annotator to your stack and set it as the active stack:

```shell
zenml stack update <YOUR_STACK_NAME> --annotator pigeon
```

Now you're ready to use the Pigeon annotator in your ML workflow!

### How do you use it?

With the Pigeon annotator registered and added to your active stack, you can easily access it using the ZenML client within your Jupyter notebook.

For text classification tasks, you can launch the Pigeon annotator as follows:

````python
from zenml.client import Client

annotator = Client().active_stack.annotator

annotations = annotator.annotate(
    data=[
        'I love this movie',
        'I was really disappointed by the book'
    ],
    options=[
        'positive',
        'negative'
    ]
)
````

For image classification tasks, you can provide a custom display function to render the images:

````python
from zenml.client import Client
from IPython.display import display, Image

annotator = Client().active_stack.annotator

annotations = annotator.annotate(
    data=[
        '/path/to/image1.png',
        '/path/to/image2.png'
    ],
    options=[
        'cat',
        'dog'
    ],
    display_fn=lambda filename: display(Image(filename))
)
````

The `launch` method returns the annotations as a list of tuples, where each tuple contains the data item and its corresponding label.

You can also use the `zenml annotator dataset` commands to manage your datasets:

* `zenml annotator dataset list` - List all available datasets
* `zenml annotator dataset delete <dataset_name>` - Delete a specific dataset
* `zenml annotator dataset stats <dataset_name>` - Get statistics for a specific dataset

Annotation files are saved as JSON files in the specified output directory. Each
annotation file represents a dataset, with the filename serving as the dataset
name.

## Acknowledgements

Pigeon was created by [Anastasis Germanidis](https://github.com/agermanidis) and
released as a [Python package](https://pypi.org/project/pigeon-jupyter/) and
[Github repository](https://github.com/agermanidis/pigeon). It is licensed under
the Apache License. It has been updated to work with more recent `ipywidgets`
versions and some small UI improvements were added. We are grateful to Anastasis
for creating this tool and making it available to the community.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
