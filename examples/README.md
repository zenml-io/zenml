## Examples

Here you can find a list of practical examples on how you can use ZenML with brief descriptions for each example:

- **airflow**: Running pipelines with airflow.
- **low_level_guide**: All the code for the low-level API guide found in the [docs](https://docs.zenml.io).
- **not_so_quickstart**: Shows of the modularity of the pipelines with hot-swapping of Tensorflow, PyTorch, and scikit-learn trainers.
- **quickstart**: The official quickstart tutorial.

For each of these examples, ZenML provides a handly CLI command to pull them directly into your local environment. First install `zenml`:

```shell
pip install zenml
```

Then you can view all the examples:

```shell
zenml example list
```

And pull individual ones:

```shell
zenml example pull EXAMPLE_NAME
# at this point a `zenml_examples` dir would be created with the examples
```

Have any questions? Want more tutorials? Spot out-dated, frustrating tutorials? We got you covered!

Feel free to let us know by creating an 
[issue](https://github.com/zenml-io/zenml/issues) here on our Github or by reaching out to us on our 
[Slack](https://zenml.io/slack-invite/). 