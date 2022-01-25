## Examples

Here you can find a list of practical examples on how you can use ZenML with
brief descriptions for each example:

Please note that at any moment this examples folder might be subject to change
on `main`. If you are using a certain version of `zenml`, you can select the
correct version on the GitHub UI at the top left side with the appropriate tag,
or visit the link directly:
`https://github.com/zenml-io/zenml/tree/<VERSION>/examples`

- **airflow_local**: Running pipelines with airflow locally.
- **caching**: Using caching to skip data-intensive tasks and save costs.
- **class_based_api**: All the code for the class-based API guide found in the
  [docs](https://docs.zenml.io/v/docs/guides/class-based-api).
- **custom_materializer**: Create a custom materializer to control data flowing between steps.
- **dag_visualizer**: Visualizing a pipeline.
- **drift_detection**: Detect drift with our Evidently integration.
- **fetch_historical_runs**: Show-cases dynamically fetching historical runs from within a step.
- **functional_api**: All the code for the functional API guide found in the
  [docs](https://docs.zenml.io/v/docs/guides/functional-api/).
- **kubeflow**: Shows how to orchestrate a pipeline a local kubeflow stack.
- **lineage**: Visualizing a pipeline run and showcasing artifact lineage.
- **mlflow_tracking**: Track and visualize experiment runs with MLFlow Tracking.
- **not_so_quickstart**: Shows of the modularity of the pipelines with
hot-swapping of Tensorflow, PyTorch, and scikit-learn trainers.
- **quickstart**: The official quickstart tutorial.
- **standard_interfaces**: This examples uses a collection of built-in and
integrated standard interfaces to showcase their effect on the overall
smoothness of the user experience.
- **statistics**: Show-cases how ZenML can automatically extract statistics
  using facets.
- **whylogs**: Show-cases [whylogs](https://github.com/whylabs/whylogs) integration.

For each of these examples, ZenML provides a handy CLI command to pull them
directly into your local environment. First install `zenml`:

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

You can now even run the example directly with a one-liner:

```shell
zenml example run EXAMPLE_NAME  # not implemented for all examples
```

Have any questions? Want more tutorials? Spot out-dated, frustrating tutorials?
We got you covered!

Feel free to let us know by creating an
[issue](https://github.com/zenml-io/zenml/issues) here on our GitHub or by
reaching out to us on our [Slack](https://zenml.io/slack-invite/). 