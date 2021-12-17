## Examples

Here you can find a list of practical examples on how you can use ZenML with brief descriptions for each example:

- **airflow_local**: Running pipelines with airflow locally.
- **caching**: Using caching to skip data-intensive tasks and save costs.
- **class_based_api**: All the code for the class-based API guide found in the [docs](https://docs.zenml.io/guides/class-based-api).
- **dag_visualizer**: Visualizing a pipeline.
- **functional_api**: All the code for the functional API guide found in the [docs](https://docs.zenml.io/guides/functional-api).
- **kubeflow**: Shows how to orchestrate a pipeline a local kubeflow stack.
- **lineage**: Visualizing a pipeline run and showcasing artifact lineage.
- **not_so_quickstart**: Shows of the modularity of the pipelines with hot-swapping of Tensorflow, PyTorch, and scikit-learn trainers.
- **quickstart**: The official quickstart tutorial.
- **standard_interfaces**: This examples uses a collection of built-in and integrated standard interfaces to showcase their effect on the overall smoothness of the user experience.
- **statistics**: Show-cases how ZenML can automatically extract statistics using facets.

For each of these examples, ZenML provides a handy CLI command to pull them directly into your local environment. First install `zenml`:

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
[issue](https://github.com/zenml-io/zenml/issues) here on our GitHub or by reaching out to us on our 
[Slack](https://zenml.io/slack-invite/). 