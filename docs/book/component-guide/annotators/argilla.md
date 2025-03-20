---
description: Annotating data using Argilla.
---

# Argilla

[Argilla](https://github.com/argilla-io/argilla) is a collaboration tool for AI engineers and domain experts who need to build high-quality datasets for their projects. It enables users to build robust language models through faster data curation using both human and machine feedback, providing support for each step in the MLOps cycle, from data labeling to model monitoring.

![Argilla Annotator](../../.gitbook/assets/argilla_annotator.png)

Argilla distinguishes itself for its focus on specific use cases and human-in-the-loop approaches. While it does offer programmatic features, Argilla's core value lies in actively involving human experts in the tool-building process, setting it apart from other competitors.

### When would you want to use it?

If you need to label textual data as part of your ML workflow, that is the point at which you could consider adding the Argilla annotator stack component as part of your ZenML stack.

We currently support the use of annotation at the various stages described in[the main annotators docs page](./). The Argilla integration currently is built to support annotation using a local (Docker-backed) instance of Argilla as well as a deployed instance of Argilla. There is an easy way to deploy Argilla as a [Hugging Face Space](https://huggingface.co/docs/hub/spaces-sdks-docker-argilla), for instance, which is documented in the [Argilla documentation](https://docs.argilla.io/latest/getting_started/quickstart/).

### How to deploy it?

The Argilla Annotator flavor is provided by the Argilla ZenML integration. You need to install it to be able to register it as an Annotator and add it to your stack:

```shell
zenml integration install argilla
```

You can either pass the `api_key` directly into the `zenml annotator register` command or you can register it as a secret and pass the secret name into the command. We recommend the latter approach for security reasons. If you want to take the latter approach, be sure to register a secret for whichever artifact store you choose, and then you should make sure to pass the name of that secret into the annotator as the `--authentication_secret`. For example, you'd run:

```shell
zenml secret create argilla_secrets --api_key="<your_argilla_api_key>"
```

(Visit the Argilla documentation and interface to obtain your API key.)

Then register your annotator with ZenML:

```shell
zenml annotator register argilla --flavor argilla --authentication_secret=argilla_secrets --port=6900
```

When using a deployed instance of Argilla, the instance URL must be specified without any trailing `/` at the end. If you are using a Hugging Face Spaces instance and its visibility is set to private, you must also set the`headers` parameter which would include a Hugging Face token. For example:

```shell
zenml annotator register argilla --flavor argilla --authentication_secret=argilla_secrets --instance_url="https://[your-owner-name]-[your_space_name].hf.space" --headers='{"Authorization": "Bearer {[your_hugging_face_token]}"}'
```

Finally, add all these components to a stack and set it as your active stack. For example:

```shell
zenml stack copy default annotation
# this must be done separately so that the other required stack components are first registered
zenml stack update annotation -an <YOUR_ARGILLA_ANNOTATOR>
zenml stack set annotation
# optionally also
zenml stack describe
```

Now if you run a simple CLI command like `zenml annotator dataset list` this should work without any errors. You're ready to use your annotator in your ML workflow!

### How do you use it?

ZenML supports access to your data and annotations via the `zenml annotator ...` CLI command. We have also implemented an interface to some of the common Argilla functionality via the ZenML SDK.

You can access information about the datasets you're using with the `zenml annotator dataset list`. To work on annotation for a particular dataset, you can run `zenml annotator dataset annotate <dataset_name>`. This will open the Argilla web interface for you to start annotating the dataset.

#### Argilla Annotator Stack Component

Our Argilla annotator component inherits from the `BaseAnnotator` class. There are some methods that are core methods that must be defined, like being able to register or get a dataset. Most annotators handle things like the storage of state and have their own custom features, so there are quite a few extra methods specific to Argilla.

The core Argilla functionality that's currently enabled includes a way to register your datasets, export any annotations for use in separate steps as well as start the annotator daemon process. (Argilla requires a server to be running in order to use the web interface, and ZenML handles the connection to this server using the details you passed in when registering the component.)

#### Argilla Annotator SDK

Visit [the SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-argilla.html) to learn more about the methods that ZenML exposes for the Argilla annotator. To access the SDK through Python, you would first get the client object and then call the methods you need. For example:

```python
from zenml.client import Client

client = Client()
annotator = client.active_stack.annotator

# list dataset names
dataset_names = annotator.get_dataset_names()

# get a specific dataset
dataset = annotator.get_dataset("dataset_name")

# get the annotations for a dataset
annotations = annotator.get_labeled_data(dataset_name="dataset_name")
```

For more detailed information on how to use the Argilla annotator and the functionality it provides, visit the [Argilla documentation](https://docs.argilla.io/latest/).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
