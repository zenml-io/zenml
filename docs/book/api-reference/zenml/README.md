# Zenml

&lt;!DOCTYPE html&gt;

zenml package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.conftest module](./#module-zenml.conftest)
      * [zenml.constants module](./#module-zenml.constants)
      * [zenml.enums module](./#module-zenml.enums)
      * [zenml.exceptions module](./#module-zenml.exceptions)
      * [zenml.logger module](./#module-zenml.logger)
      * [zenml.version module](./#module-zenml.version)
      * [Module contents](./#module-zenml)
* [ « zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
* [ zenml.backend... »](zenml.backends/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.rst.txt)

## zenml package[¶](./#zenml-package)

### Subpackages[¶](./#subpackages)

* [zenml.backends package](zenml.backends/)
  * [Subpackages](zenml.backends/#subpackages)
    * [zenml.backends.orchestrator package](zenml.backends/zenml.backends.orchestrator/)
      * [Subpackages](zenml.backends/zenml.backends.orchestrator/#subpackages)
      * [Submodules](zenml.backends/zenml.backends.orchestrator/#submodules)
      * [zenml.backends.orchestrator.entrypoint module](zenml.backends/zenml.backends.orchestrator/#module-zenml.backends.orchestrator.entrypoint)
      * [Module contents](zenml.backends/zenml.backends.orchestrator/#module-zenml.backends.orchestrator)
    * [zenml.backends.processing package](zenml.backends/zenml.backends.processing.md)
      * [Submodules](zenml.backends/zenml.backends.processing.md#submodules)
      * [zenml.backends.processing.processing\_base\_backend module](zenml.backends/zenml.backends.processing.md#module-zenml.backends.processing.processing_base_backend)
      * [zenml.backends.processing.processing\_dataflow\_backend module](zenml.backends/zenml.backends.processing.md#module-zenml.backends.processing.processing_dataflow_backend)
      * [zenml.backends.processing.processing\_spark\_backend module](zenml.backends/zenml.backends.processing.md#module-zenml.backends.processing.processing_spark_backend)
      * [Module contents](zenml.backends/zenml.backends.processing.md#module-zenml.backends.processing)
    * [zenml.backends.training package](zenml.backends/zenml.backends.training.md)
      * [Submodules](zenml.backends/zenml.backends.training.md#submodules)
      * [zenml.backends.training.training\_base\_backend module](zenml.backends/zenml.backends.training.md#module-zenml.backends.training.training_base_backend)
      * [zenml.backends.training.training\_gcaip\_backend module](zenml.backends/zenml.backends.training.md#module-zenml.backends.training.training_gcaip_backend)
      * [Module contents](zenml.backends/zenml.backends.training.md#module-zenml.backends.training)
  * [Submodules](zenml.backends/#submodules)
  * [zenml.backends.base\_backend module](zenml.backends/#module-zenml.backends.base_backend)
  * [zenml.backends.base\_backend\_test module](zenml.backends/#module-zenml.backends.base_backend_test)
  * [Module contents](zenml.backends/#module-zenml.backends)
* [zenml.cli package](zenml.cli.md)
  * [Submodules](zenml.cli.md#submodules)
  * [zenml.cli.base module](zenml.cli.md#module-zenml.cli.base)
  * [zenml.cli.cli module](zenml.cli.md#module-zenml.cli.cli)
  * [zenml.cli.config module](zenml.cli.md#module-zenml.cli.config)
  * [zenml.cli.datasource module](zenml.cli.md#module-zenml.cli.datasource)
  * [zenml.cli.pipeline module](zenml.cli.md#module-zenml.cli.pipeline)
  * [zenml.cli.step module](zenml.cli.md#module-zenml.cli.step)
  * [zenml.cli.utils module](zenml.cli.md#module-zenml.cli.utils)
  * [zenml.cli.version module](zenml.cli.md#module-zenml.cli.version)
  * [Module contents](zenml.cli.md#module-zenml.cli)
* [zenml.components package](zenml.components/)
  * [Subpackages](zenml.components/#subpackages)
    * [zenml.components.bulk\_inferrer package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#submodules)
      * [zenml.components.bulk\_inferrer.component module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#module-zenml.components.bulk_inferrer.component)
      * [zenml.components.bulk\_inferrer.constants module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#module-zenml.components.bulk_inferrer.constants)
      * [zenml.components.bulk\_inferrer.executor module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#module-zenml.components.bulk_inferrer.executor)
      * [zenml.components.bulk\_inferrer.utils module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#module-zenml.components.bulk_inferrer.utils)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.bulk_inferrer.html#module-zenml.components.bulk_inferrer)
    * [zenml.components.data\_gen package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#submodules)
      * [zenml.components.data\_gen.component module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#module-zenml.components.data_gen.component)
      * [zenml.components.data\_gen.constants module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#module-zenml.components.data_gen.constants)
      * [zenml.components.data\_gen.executor module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#module-zenml.components.data_gen.executor)
      * [zenml.components.data\_gen.utils module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#module-zenml.components.data_gen.utils)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.data_gen.html#module-zenml.components.data_gen)
    * [zenml.components.evaluator package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html#submodules)
      * [zenml.components.evaluator.component module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html#module-zenml.components.evaluator.component)
      * [zenml.components.evaluator.constants module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html#module-zenml.components.evaluator.constants)
      * [zenml.components.evaluator.executor module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html#module-zenml.components.evaluator.executor)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html#module-zenml.components.evaluator)
    * [zenml.components.pusher package](zenml.components/zenml.components.pusher.md)
      * [Submodules](zenml.components/zenml.components.pusher.md#submodules)
      * [zenml.components.pusher.cortex\_executor module](zenml.components/zenml.components.pusher.md#module-zenml.components.pusher.cortex_executor)
      * [Module contents](zenml.components/zenml.components.pusher.md#module-zenml.components.pusher)
    * [zenml.components.sequencer package](zenml.components/zenml.components.sequencer.md)
      * [Submodules](zenml.components/zenml.components.sequencer.md#submodules)
      * [zenml.components.sequencer.component module](zenml.components/zenml.components.sequencer.md#module-zenml.components.sequencer.component)
      * [zenml.components.sequencer.constants module](zenml.components/zenml.components.sequencer.md#module-zenml.components.sequencer.constants)
      * [zenml.components.sequencer.executor module](zenml.components/zenml.components.sequencer.md#module-zenml.components.sequencer.executor)
      * [zenml.components.sequencer.utils module](zenml.components/zenml.components.sequencer.md#module-zenml.components.sequencer.utils)
      * [Module contents](zenml.components/zenml.components.sequencer.md#module-zenml.components.sequencer)
    * [zenml.components.split\_gen package](zenml.components/zenml.components.split_gen.md)
      * [Submodules](zenml.components/zenml.components.split_gen.md#submodules)
      * [zenml.components.split\_gen.component module](zenml.components/zenml.components.split_gen.md#module-zenml.components.split_gen.component)
      * [zenml.components.split\_gen.constants module](zenml.components/zenml.components.split_gen.md#module-zenml.components.split_gen.constants)
      * [zenml.components.split\_gen.executor module](zenml.components/zenml.components.split_gen.md#module-zenml.components.split_gen.executor)
      * [zenml.components.split\_gen.utils module](zenml.components/zenml.components.split_gen.md#module-zenml.components.split_gen.utils)
      * [Module contents](zenml.components/zenml.components.split_gen.md#module-zenml.components.split_gen)
    * [zenml.components.tokenizer package](zenml.components/zenml.components.tokenizer.md)
      * [Submodules](zenml.components/zenml.components.tokenizer.md#submodules)
      * [zenml.components.tokenizer.component module](zenml.components/zenml.components.tokenizer.md#module-zenml.components.tokenizer.component)
      * [zenml.components.tokenizer.constants module](zenml.components/zenml.components.tokenizer.md#module-zenml.components.tokenizer.constants)
      * [zenml.components.tokenizer.executor module](zenml.components/zenml.components.tokenizer.md#module-zenml.components.tokenizer.executor)
      * [Module contents](zenml.components/zenml.components.tokenizer.md#module-zenml.components.tokenizer)
    * [zenml.components.trainer package](zenml.components/zenml.components.trainer.md)
      * [Submodules](zenml.components/zenml.components.trainer.md#submodules)
      * [zenml.components.trainer.component module](zenml.components/zenml.components.trainer.md#module-zenml.components.trainer.component)
      * [zenml.components.trainer.constants module](zenml.components/zenml.components.trainer.md#module-zenml.components.trainer.constants)
      * [zenml.components.trainer.executor module](zenml.components/zenml.components.trainer.md#module-zenml.components.trainer.executor)
      * [zenml.components.trainer.trainer\_module module](zenml.components/zenml.components.trainer.md#module-zenml.components.trainer.trainer_module)
      * [Module contents](zenml.components/zenml.components.trainer.md#module-zenml.components.trainer)
    * [zenml.components.transform package](zenml.components/zenml.components.transform.md)
      * [Submodules](zenml.components/zenml.components.transform.md#submodules)
      * [zenml.components.transform.transform\_module module](zenml.components/zenml.components.transform.md#module-zenml.components.transform.transform_module)
      * [Module contents](zenml.components/zenml.components.transform.md#module-zenml.components.transform)
    * [zenml.components.transform\_simple package](zenml.components/zenml.components.transform_simple.md)
      * [Submodules](zenml.components/zenml.components.transform_simple.md#submodules)
      * [zenml.components.transform\_simple.component module](zenml.components/zenml.components.transform_simple.md#module-zenml.components.transform_simple.component)
      * [zenml.components.transform\_simple.constants module](zenml.components/zenml.components.transform_simple.md#module-zenml.components.transform_simple.constants)
      * [zenml.components.transform\_simple.executor module](zenml.components/zenml.components.transform_simple.md#module-zenml.components.transform_simple.executor)
      * [zenml.components.transform\_simple.utils module](zenml.components/zenml.components.transform_simple.md#module-zenml.components.transform_simple.utils)
      * [Module contents](zenml.components/zenml.components.transform_simple.md#module-zenml.components.transform_simple)
  * [Module contents](zenml.components/#module-zenml.components)
* [zenml.datasources package](zenml.datasources.md)
  * [Submodules](zenml.datasources.md#submodules)
  * [zenml.datasources.base\_datasource module](zenml.datasources.md#module-zenml.datasources.base_datasource)
  * [zenml.datasources.base\_datasource\_test module](zenml.datasources.md#module-zenml.datasources.base_datasource_test)
  * [zenml.datasources.bq\_datasource module](zenml.datasources.md#module-zenml.datasources.bq_datasource)
  * [zenml.datasources.csv\_datasource module](zenml.datasources.md#module-zenml.datasources.csv_datasource)
  * [zenml.datasources.image\_datasource module](zenml.datasources.md#module-zenml.datasources.image_datasource)
  * [zenml.datasources.json\_datasource module](zenml.datasources.md#module-zenml.datasources.json_datasource)
  * [zenml.datasources.numpy\_datasource module](zenml.datasources.md#module-zenml.datasources.numpy_datasource)
  * [zenml.datasources.pandas\_datasource module](zenml.datasources.md#module-zenml.datasources.pandas_datasource)
  * [zenml.datasources.postgres\_datasource module](zenml.datasources.md#zenml-datasources-postgres-datasource-module)
  * [Module contents](zenml.datasources.md#module-zenml.datasources)
* [zenml.metadata package](zenml.metadata.md)
  * [Submodules](zenml.metadata.md#submodules)
  * [zenml.metadata.metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper)
  * [zenml.metadata.metadata\_wrapper\_factory module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_factory)
  * [zenml.metadata.metadata\_wrapper\_test module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_test)
  * [zenml.metadata.mock\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mock_metadata_wrapper)
  * [zenml.metadata.mysql\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mysql_metadata_wrapper)
  * [zenml.metadata.sqlite\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.sqlite_metadata_wrapper)
  * [Module contents](zenml.metadata.md#module-zenml.metadata)
* [zenml.pipelines package](zenml.pipelines.md)
  * [Submodules](zenml.pipelines.md#submodules)
  * [zenml.pipelines.base\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.base_pipeline)
  * [zenml.pipelines.base\_pipeline\_test module](zenml.pipelines.md#module-zenml.pipelines.base_pipeline_test)
  * [zenml.pipelines.data\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.data_pipeline)
  * [zenml.pipelines.deploy\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.deploy_pipeline)
  * [zenml.pipelines.infer\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.infer_pipeline)
  * [zenml.pipelines.nlp\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.nlp_pipeline)
  * [zenml.pipelines.training\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.training_pipeline)
  * [zenml.pipelines.training\_pipeline\_test module](zenml.pipelines.md#module-zenml.pipelines.training_pipeline_test)
  * [zenml.pipelines.utils module](zenml.pipelines.md#module-zenml.pipelines.utils)
  * [Module contents](zenml.pipelines.md#module-zenml.pipelines)
* [zenml.repo package](zenml.repo.md)
  * [Submodules](zenml.repo.md#submodules)
  * [zenml.repo.artifact\_store module](zenml.repo.md#module-zenml.repo.artifact_store)
  * [zenml.repo.constants module](zenml.repo.md#module-zenml.repo.constants)
  * [zenml.repo.git\_wrapper module](zenml.repo.md#module-zenml.repo.git_wrapper)
  * [zenml.repo.global\_config module](zenml.repo.md#module-zenml.repo.global_config)
  * [zenml.repo.repo module](zenml.repo.md#module-zenml.repo.repo)
  * [zenml.repo.repo\_test module](zenml.repo.md#module-zenml.repo.repo_test)
  * [zenml.repo.zenml\_config module](zenml.repo.md#module-zenml.repo.zenml_config)
  * [zenml.repo.zenml\_config\_test module](zenml.repo.md#module-zenml.repo.zenml_config_test)
  * [Module contents](zenml.repo.md#module-zenml.repo)
* [zenml.standards package](zenml.standards.md)
  * [Submodules](zenml.standards.md#submodules)
  * [zenml.standards.standard\_keys module](zenml.standards.md#module-zenml.standards.standard_keys)
  * [Module contents](zenml.standards.md#module-zenml.standards)
* [zenml.steps package](zenml.steps/)
  * [Subpackages](zenml.steps/#subpackages)
    * [zenml.steps.data package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#submodules)
      * [zenml.steps.data.base\_data\_step module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.base_data_step)
      * [zenml.steps.data.bq\_data\_step module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.bq_data_step)
      * [zenml.steps.data.csv\_data\_step module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.csv_data_step)
      * [zenml.steps.data.image\_data\_step module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.image_data_step)
      * [zenml.steps.data.image\_step\_test module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.image_step_test)
      * [zenml.steps.data.postgres\_data\_step module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data.postgres_data_step)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.data.html#module-zenml.steps.data)
    * [zenml.steps.deployer package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#submodules)
      * [zenml.steps.deployer.base\_deployer module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#module-zenml.steps.deployer.base_deployer)
      * [zenml.steps.deployer.cortex\_deployer module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#module-zenml.steps.deployer.cortex_deployer)
      * [zenml.steps.deployer.gcaip\_deployer module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#module-zenml.steps.deployer.gcaip_deployer)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#module-zenml.steps.deployer)
    * [zenml.steps.evaluator package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#submodules)
      * [zenml.steps.evaluator.agnostic\_evaluator module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#module-zenml.steps.evaluator.agnostic_evaluator)
      * [zenml.steps.evaluator.base\_evaluator module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#module-zenml.steps.evaluator.base_evaluator)
      * [zenml.steps.evaluator.tfma\_evaluator module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#module-zenml.steps.evaluator.tfma_evaluator)
      * [zenml.steps.evaluator.tfma\_module module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#module-zenml.steps.evaluator.tfma_module)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#module-zenml.steps.evaluator)
    * [zenml.steps.inferrer package](zenml.steps/zenml.steps.inferrer.md)
      * [Submodules](zenml.steps/zenml.steps.inferrer.md#submodules)
      * [zenml.steps.inferrer.base\_inferrer\_step module](zenml.steps/zenml.steps.inferrer.md#module-zenml.steps.inferrer.base_inferrer_step)
      * [zenml.steps.inferrer.inference\_file\_writer\_step module](zenml.steps/zenml.steps.inferrer.md#module-zenml.steps.inferrer.inference_file_writer_step)
      * [zenml.steps.inferrer.tensorflow\_inferrer\_step module](zenml.steps/zenml.steps.inferrer.md#module-zenml.steps.inferrer.tensorflow_inferrer_step)
      * [Module contents](zenml.steps/zenml.steps.inferrer.md#module-zenml.steps.inferrer)
    * [zenml.steps.preprocesser package](zenml.steps/zenml.steps.preprocesser/)
      * [Subpackages](zenml.steps/zenml.steps.preprocesser/#subpackages)
      * [Submodules](zenml.steps/zenml.steps.preprocesser/#submodules)
      * [zenml.steps.preprocesser.base\_preprocesser module](zenml.steps/zenml.steps.preprocesser/#module-zenml.steps.preprocesser.base_preprocesser)
      * [Module contents](zenml.steps/zenml.steps.preprocesser/#module-zenml.steps.preprocesser)
    * [zenml.steps.sequencer package](zenml.steps/zenml.steps.sequencer/)
      * [Subpackages](zenml.steps/zenml.steps.sequencer/#subpackages)
      * [Submodules](zenml.steps/zenml.steps.sequencer/#submodules)
      * [zenml.steps.sequencer.base\_sequencer module](zenml.steps/zenml.steps.sequencer/#module-zenml.steps.sequencer.base_sequencer)
      * [Module contents](zenml.steps/zenml.steps.sequencer/#module-zenml.steps.sequencer)
    * [zenml.steps.split package](zenml.steps/zenml.steps.split.md)
      * [Submodules](zenml.steps/zenml.steps.split.md#submodules)
      * [zenml.steps.split.base\_split\_step module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.base_split_step)
      * [zenml.steps.split.categorical\_domain\_split\_step module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.categorical_domain_split_step)
      * [zenml.steps.split.categorical\_ratio\_split\_step module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.categorical_ratio_split_step)
      * [zenml.steps.split.constants module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.constants)
      * [zenml.steps.split.no\_split\_step module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.no_split_step)
      * [zenml.steps.split.random\_split module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.random_split)
      * [zenml.steps.split.split\_step\_test module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.split_step_test)
      * [zenml.steps.split.utils module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.utils)
      * [zenml.steps.split.utils\_test module](zenml.steps/zenml.steps.split.md#module-zenml.steps.split.utils_test)
      * [Module contents](zenml.steps/zenml.steps.split.md#module-zenml.steps.split)
    * [zenml.steps.tokenizer package](zenml.steps/zenml.steps.tokenizer.md)
      * [Submodules](zenml.steps/zenml.steps.tokenizer.md#submodules)
      * [zenml.steps.tokenizer.base\_tokenizer module](zenml.steps/zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.base_tokenizer)
      * [zenml.steps.tokenizer.hf\_tokenizer module](zenml.steps/zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.hf_tokenizer)
      * [zenml.steps.tokenizer.utils module](zenml.steps/zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.utils)
      * [Module contents](zenml.steps/zenml.steps.tokenizer.md#module-zenml.steps.tokenizer)
    * [zenml.steps.trainer package](zenml.steps/zenml.steps.trainer/)
      * [Subpackages](zenml.steps/zenml.steps.trainer/#subpackages)
      * [Submodules](zenml.steps/zenml.steps.trainer/#submodules)
      * [zenml.steps.trainer.base\_trainer module](zenml.steps/zenml.steps.trainer/#module-zenml.steps.trainer.base_trainer)
      * [zenml.steps.trainer.utils module](zenml.steps/zenml.steps.trainer/#module-zenml.steps.trainer.utils)
      * [Module contents](zenml.steps/zenml.steps.trainer/#module-zenml.steps.trainer)
  * [Submodules](zenml.steps/#submodules)
  * [zenml.steps.base\_step module](zenml.steps/#module-zenml.steps.base_step)
  * [zenml.steps.base\_step\_test module](zenml.steps/#module-zenml.steps.base_step_test)
  * [Module contents](zenml.steps/#module-zenml.steps)
* [zenml.utils package](zenml.utils/)
  * [Subpackages](zenml.utils/#subpackages)
    * [zenml.utils.post\_training package](zenml.utils/zenml.utils.post_training.md)
      * [Submodules](zenml.utils/zenml.utils.post_training.md#submodules)
      * [zenml.utils.post\_training.compare module](zenml.utils/zenml.utils.post_training.md#module-zenml.utils.post_training.compare)
      * [zenml.utils.post\_training.post\_training\_utils module](zenml.utils/zenml.utils.post_training.md#module-zenml.utils.post_training.post_training_utils)
      * [Module contents](zenml.utils/zenml.utils.post_training.md#module-zenml.utils.post_training)
  * [Submodules](zenml.utils/#submodules)
  * [zenml.utils.analytics\_utils module](zenml.utils/#module-zenml.utils.analytics_utils)
  * [zenml.utils.naming\_utils module](zenml.utils/#module-zenml.utils.naming_utils)
  * [zenml.utils.path\_utils module](zenml.utils/#module-zenml.utils.path_utils)
  * [zenml.utils.preprocessing\_utils module](zenml.utils/#module-zenml.utils.preprocessing_utils)
  * [zenml.utils.print\_utils module](zenml.utils/#module-zenml.utils.print_utils)
  * [zenml.utils.requirement\_utils module](zenml.utils/#module-zenml.utils.requirement_utils)
  * [zenml.utils.source\_utils module](zenml.utils/#module-zenml.utils.source_utils)
  * [zenml.utils.string\_utils module](zenml.utils/#module-zenml.utils.string_utils)
  * [zenml.utils.yaml\_utils module](zenml.utils/#module-zenml.utils.yaml_utils)
  * [Module contents](zenml.utils/#module-zenml.utils)

### Submodules[¶](./#submodules)

### zenml.conftest module[¶](./#module-zenml.conftest)

 `zenml.conftest.cleanup`\(_cleanup\_metadata\_store_, _cleanup\_artifacts_\)[¶](./#zenml.conftest.cleanup) `zenml.conftest.cleanup_artifacts`\(\)[¶](./#zenml.conftest.cleanup_artifacts) `zenml.conftest.cleanup_metadata_store`\(\)[¶](./#zenml.conftest.cleanup_metadata_store) `zenml.conftest.cleanup_pipelines_dir`\(\)[¶](./#zenml.conftest.cleanup_pipelines_dir) `zenml.conftest.delete_config`\(\)[¶](./#zenml.conftest.delete_config) `zenml.conftest.equal_backends`\(\)[¶](./#zenml.conftest.equal_backends) `zenml.conftest.equal_datasources`\(_equal\_steps_\)[¶](./#zenml.conftest.equal_datasources) `zenml.conftest.equal_md_stores`\(\)[¶](./#zenml.conftest.equal_md_stores) `zenml.conftest.equal_pipelines`\(_equal\_backends_, _equal\_steps_, _equal\_datasources_\)[¶](./#zenml.conftest.equal_pipelines) `zenml.conftest.equal_steps`\(_equal\_backends_\)[¶](./#zenml.conftest.equal_steps) `zenml.conftest.equal_zenml_configs`\(_equal\_md\_stores_\)[¶](./#zenml.conftest.equal_zenml_configs) `zenml.conftest.repo`\(\)[¶](./#zenml.conftest.repo)

### zenml.constants module[¶](./#module-zenml.constants)

 `zenml.constants.handle_bool_env_var`\(_var_, _default=False_\)[¶](./#zenml.constants.handle_bool_env_var)

Converts normal env var to boolean

### zenml.enums module[¶](./#module-zenml.enums)

 _class_ `zenml.enums.ArtifactStoreTypes`\(_value_\)[¶](./#zenml.enums.ArtifactStoreTypes)

Bases: `enum.Enum`

An enumeration. `gcs` _= 2_[¶](./#zenml.enums.ArtifactStoreTypes.gcs) `local` _= 1_[¶](./#zenml.enums.ArtifactStoreTypes.local) _class_ `zenml.enums.GCPGPUTypes`\(_value_\)[¶](./#zenml.enums.GCPGPUTypes)

Bases: `enum.Enum`

An enumeration. `K80` _= 1_[¶](./#zenml.enums.GCPGPUTypes.K80) `P100` _= 3_[¶](./#zenml.enums.GCPGPUTypes.P100) `V100` _= 2_[¶](./#zenml.enums.GCPGPUTypes.V100) _class_ `zenml.enums.GDPComponent`\(_value_\)[¶](./#zenml.enums.GDPComponent)

Bases: `enum.Enum`

An enumeration. `DataGen` _= 16_[¶](./#zenml.enums.GDPComponent.DataGen) `DataSchema` _= 19_[¶](./#zenml.enums.GDPComponent.DataSchema) `DataStatistics` _= 18_[¶](./#zenml.enums.GDPComponent.DataStatistics) `Deployer` _= 15_[¶](./#zenml.enums.GDPComponent.Deployer) `Evaluator` _= 12_[¶](./#zenml.enums.GDPComponent.Evaluator) `Inferrer` _= 17_[¶](./#zenml.enums.GDPComponent.Inferrer) `ModelValidator` _= 14_[¶](./#zenml.enums.GDPComponent.ModelValidator) `PreTransform` _= 7_[¶](./#zenml.enums.GDPComponent.PreTransform) `PreTransformSchema` _= 9_[¶](./#zenml.enums.GDPComponent.PreTransformSchema) `PreTransformStatistics` _= 8_[¶](./#zenml.enums.GDPComponent.PreTransformStatistics) `ResultPackager` _= 13_[¶](./#zenml.enums.GDPComponent.ResultPackager) `Sequencer` _= 4_[¶](./#zenml.enums.GDPComponent.Sequencer) `SequencerSchema` _= 6_[¶](./#zenml.enums.GDPComponent.SequencerSchema) `SequencerStatistics` _= 5_[¶](./#zenml.enums.GDPComponent.SequencerStatistics) `SplitGen` _= 1_[¶](./#zenml.enums.GDPComponent.SplitGen) `SplitSchema` _= 3_[¶](./#zenml.enums.GDPComponent.SplitSchema) `SplitStatistics` _= 2_[¶](./#zenml.enums.GDPComponent.SplitStatistics) `Tokenizer` _= 20_[¶](./#zenml.enums.GDPComponent.Tokenizer) `Trainer` _= 11_[¶](./#zenml.enums.GDPComponent.Trainer) `Transform` _= 10_[¶](./#zenml.enums.GDPComponent.Transform) _class_ `zenml.enums.ImagePullPolicy`\(_value_\)[¶](./#zenml.enums.ImagePullPolicy)

Bases: `enum.Enum`

An enumeration. `Always` _= 1_[¶](./#zenml.enums.ImagePullPolicy.Always) `IfNotPresent` _= 3_[¶](./#zenml.enums.ImagePullPolicy.IfNotPresent) `Never` _= 2_[¶](./#zenml.enums.ImagePullPolicy.Never) _class_ `zenml.enums.MLMetadataTypes`\(_value_\)[¶](./#zenml.enums.MLMetadataTypes)

Bases: `enum.Enum`

An enumeration. `mock` _= 3_[¶](./#zenml.enums.MLMetadataTypes.mock) `mysql` _= 2_[¶](./#zenml.enums.MLMetadataTypes.mysql) `sqlite` _= 1_[¶](./#zenml.enums.MLMetadataTypes.sqlite) _class_ `zenml.enums.PipelineStatusTypes`\(_value_\)[¶](./#zenml.enums.PipelineStatusTypes)

Bases: `enum.Enum`

An enumeration. `Failed` _= 2_[¶](./#zenml.enums.PipelineStatusTypes.Failed) `NotStarted` _= 1_[¶](./#zenml.enums.PipelineStatusTypes.NotStarted) `Running` _= 4_[¶](./#zenml.enums.PipelineStatusTypes.Running) `Succeeded` _= 3_[¶](./#zenml.enums.PipelineStatusTypes.Succeeded) _class_ `zenml.enums.StepTypes`\(_value_\)[¶](./#zenml.enums.StepTypes)

Bases: `enum.Enum`

An enumeration. `base` _= 1_[¶](./#zenml.enums.StepTypes.base) `data` _= 2_[¶](./#zenml.enums.StepTypes.data) `deployer` _= 8_[¶](./#zenml.enums.StepTypes.deployer) `evaluator` _= 7_[¶](./#zenml.enums.StepTypes.evaluator) `inferrer` _= 9_[¶](./#zenml.enums.StepTypes.inferrer) `preprocesser` _= 4_[¶](./#zenml.enums.StepTypes.preprocesser) `sequencer` _= 3_[¶](./#zenml.enums.StepTypes.sequencer) `split` _= 5_[¶](./#zenml.enums.StepTypes.split) `trainer` _= 6_[¶](./#zenml.enums.StepTypes.trainer)

### zenml.exceptions module[¶](./#module-zenml.exceptions)

ZenML specific exception definitions _exception_ `zenml.exceptions.AlreadyExistsException`\(_name=''_, _resource\_type=''_\)[¶](./#zenml.exceptions.AlreadyExistsException)

Bases: `Exception`

Raises exception when the name already exist in the system but an action is trying to create a resource with the same name. _exception_ `zenml.exceptions.DoesNotExistException`\(_name=''_, _reason=''_, _message='{} does not exist! This might be due to: {}'_\)[¶](./#zenml.exceptions.DoesNotExistException)

Bases: `Exception`

Raises exception when the name does not exist in the system but an action is being done that requires it to be present. _exception_ `zenml.exceptions.EmptyDatasourceException`\(_message='This datasource has not been used in any pipelines, therefore the associated data has no versions. Please use this datasouce in any ZenML pipeline with \`pipeline.add\_datasource\(datasource\)\`'_\)[¶](./#zenml.exceptions.EmptyDatasourceException)

Bases: `Exception`

Raises exception when a datasource data is accessed without running an associated pipeline. _exception_ `zenml.exceptions.InitializationException`\(_message='ZenML config is none. Did you do \`zenml init\`?'_\)[¶](./#zenml.exceptions.InitializationException)

Bases: `Exception`

Raises exception when a function is run before zenml initialization. _exception_ `zenml.exceptions.PipelineNotSucceededException`\(_name=''_, _message='{} is not yet completed successfully.'_\)[¶](./#zenml.exceptions.PipelineNotSucceededException)

Bases: `Exception`

Raises exception when trying to fetch artifacts from a not succeeded pipeline.

### zenml.logger module[¶](./#module-zenml.logger)

 `zenml.logger.get_console_handler`\(\)[¶](./#zenml.logger.get_console_handler) `zenml.logger.get_file_handler`\(\)[¶](./#zenml.logger.get_file_handler) `zenml.logger.get_logger`\(_logger\_name_\)[¶](./#zenml.logger.get_logger) `zenml.logger.init_logging`\(\)[¶](./#zenml.logger.init_logging) `zenml.logger.resolve_logging_level`\(\)[¶](./#zenml.logger.resolve_logging_level) `zenml.logger.set_root_verbosity`\(\)[¶](./#zenml.logger.set_root_verbosity)

### zenml.version module[¶](./#module-zenml.version)

This module contains project version information.

### Module contents[¶](./#module-zenml)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


