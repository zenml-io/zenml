# Configure the notebook path

When running a pipeline with steps defined in a notebook, ZenML needs to figure out which notebook you're running to extract the notebook cell code.

## Automatic detection with the `notebook` extra

If you install the `notebook` extra (e.g. `pip install "zenml[notebook]"`), ZenML will try to automatically detect which notebook you're running your pipeline from. If the automatic detection fails, you can [use an environment variable](#using-an-environment-variable) instead.

## Using an environment variable

You can use the `ZENML_NOTEBOOK_PATH` environment variable to point ZenML towards the notebook that you're running.

```bash
export ZENML_NOTEBOOK_PATH=<PATH_TO_YOUR_NOTEBOOK>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
