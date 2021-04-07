# Creating custom logic

All components of ZenML are split into two categories: The `Standard` components, i.e., the code shipped with the package, and the `User-defined` components, the code written by users to inject their own custom logic into the framework.

## Types of ZenML components

Custom logic can be added to ZenML by extending the following standard components:

* [Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/getting-started/steps/what-is-a-step.md)
* [Datasources](../datasources/what-is-a-datasource.md)
* [Pipelines](../pipelines/what-is-a-pipeline.md)
* [Backends](../backends/what-is-a-backend.md)

Each component has its own section in the docs and its own rules of precisely how to add your own. The above links will guide you through these rules.

## Rules of custom logic

While each component has its own rules, there are some rules that are general when adding your own custom logic:

* All components have `Base` classes, e.g., `BaseDatasource`, `BasePipeline`, `BaseStep` etc that need to be inherited from

  in order create your own custom logic.

* All custom classes must exist within its own `module` \(directory\) in a ZenML repo.
* All components follow the same Git-pinning methodology outlined [here](../repository/integration-with-git.md)

## Environment and custom dependencies

ZenML comes pre-installed with some common ML libraries. These include:

* `tfx` &gt;= 0.25.0
* `tensorflow` &gt;= 2.3.0
* `apache-beam` &gt;= 2.26.0
* `plotly` &gt;= 4.0.0
* `numpy` &gt;= 1.18.0

The full list can be found [here](https://github.com/maiot-io/zenml/blob/main/setup.py).

You can install any other dependencies alongisde of ZenML and use them in your code as long as they do not conflict with the dependencies listed above. E.g `torch`, `scikit-learn`, `pandas` etc are perfectly fine. However, using `tensoflow` &lt; 2.3.0 currently is not supported.

