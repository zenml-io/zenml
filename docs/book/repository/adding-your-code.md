# Adding your code in ZenML

All components of ZenML are split into two categories: The `Standard` components, i.e., the code shipped with the 
package, and the `User-defined` components, the code written by users to inject their own custom logic into the framework.

## Types of ZenML components
Currently, ZenML can be extended in the following ways:

* [Steps](../steps/what-is-a-step.md)
* [Datasources](../datasources/what-is-a-datasource.md)
* [Pipelines](../pipelines/what-is-a-pipeline.md)
* [Backends](../backends/what-is-a-backend.md)

Each component has its own section in the docs and its own rules of precisely how to add your own. The above links will 
guide you through these rules.

## Rules of custom logic
While each component has its own rules, there are some rules that are general when adding your own custom logic:

* All components have `Base` classes, e.g., `BaseDatasource`, `BasePipeline`, `BaseStep` etc that need to be inherited from 
in order create your own custom logic.
* All custom classes must exist within its own `module` (directory) in a ZenML repo.
* All components follow the same Git-pinning ideology outlined [here](integration-with-git.md)
