# Pipelines

&lt;!DOCTYPE html&gt;

zenml.pipelines package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.pipelines.md)
  * * [zenml.pipelines package](zenml.pipelines.md)
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
* [ « zenml.metadat...](zenml.metadata.md)
* [ zenml.repo package »](zenml.repo.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.pipelines.rst.txt)

## zenml.pipelines package[¶](zenml.pipelines.md#zenml-pipelines-package)

### Submodules[¶](zenml.pipelines.md#submodules)

### zenml.pipelines.base\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.base_pipeline)

Base High-level ZenML Pipeline definition _class_ `zenml.pipelines.base_pipeline.BasePipeline`\(_name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_, _\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

Bases: `object`

Base class for all ZenML pipelines.

Every ZenML pipeline should override this class. `PIPELINE_TYPE` _= 'base'_[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.PIPELINE_TYPE) `add_datasource`\(_datasource:_ [_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.add_datasource)

Add datasource to pipeline.Parameters

**datasource** – class of type BaseDatasource `copy`\(_new\_name: str_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.copy)

Deep copy the pipeline and therefore remove mutability requirement.Parameters

**new\_name** \(_str_\) – New name for copied pipeline. `create_pipeline_name_from_name`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.create_pipeline_name_from_name)

Creates a unique pipeline name from user-provided name. _classmethod_ `from_config`\(_config: Dict_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.from_config)

Convert from pipeline config to ZenML Pipeline object.

All steps are also populated and configuration set to parameters set in the config file.Parameters

**config** – a ZenML config in dict-form \(probably loaded from YAML\). `get_artifacts_uri_by_component`\(_\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_artifacts_uri_by_component) _static_ `get_name_from_pipeline_name`\(_pipeline\_name: str_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_name_from_pipeline_name)

Gets name from pipeline name.Parameters

**pipeline\_name** \(_str_\) – simple string name. `get_pipeline_config`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_pipeline_config)

Get pipeline config `get_status`\(\) → str[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_status)

Get status of pipeline. `get_steps_config`\(\) → Dict[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_steps_config)

Convert Step classes to steps config dict. _abstract_ `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_tfx_component_list)

Converts config to TFX components list. This is the point in the framework where ZenML Steps get translated into TFX pipelines.Parameters

**config** – dict of ZenML config. _property_ `is_executed_in_metadata_store`[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.is_executed_in_metadata_store) `load_config`\(\) → Dict\[str, Any\][¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.load_config)

Loads a config dict from yaml file. `register_pipeline`\(_config: Dict\[str, Any\]_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.register_pipeline)

Registers a pipeline in the artifact store as a YAML file.Parameters

**config** – dict representation of ZenML config. `run`\(_\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.run) `run_config`\(_config: Dict\[str, Any\]_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.run_config)

Gets TFX pipeline from config.Parameters

**config** – dict of ZenML config. _abstract_ `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.steps_completed)

Returns True if all steps complete, else raises exception `to_config`\(\) → Dict[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.to_config)

Converts entire pipeline to ZenML config.

### zenml.pipelines.base\_pipeline\_test module[¶](zenml.pipelines.md#module-zenml.pipelines.base_pipeline_test)

 `zenml.pipelines.base_pipeline_test.test_add_datasource`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_add_datasource) `zenml.pipelines.base_pipeline_test.test_executed`\(_repo_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_executed) `zenml.pipelines.base_pipeline_test.test_get_artifacts_uri_by_component`\(_repo_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_get_artifacts_uri_by_component) `zenml.pipelines.base_pipeline_test.test_get_pipeline_config`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_get_pipeline_config) `zenml.pipelines.base_pipeline_test.test_get_status`\(_repo_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_get_status) `zenml.pipelines.base_pipeline_test.test_get_steps_config`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_get_steps_config) `zenml.pipelines.base_pipeline_test.test_load_config`\(_repo_, _equal\_pipelines_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_load_config) `zenml.pipelines.base_pipeline_test.test_naming`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_naming) `zenml.pipelines.base_pipeline_test.test_pipeline_copy`\(_repo_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_pipeline_copy) `zenml.pipelines.base_pipeline_test.test_register_pipeline`\(_repo_, _delete\_config_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_register_pipeline) `zenml.pipelines.base_pipeline_test.test_run_base`\(_delete\_config_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_run_base) `zenml.pipelines.base_pipeline_test.test_run_config`\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_run_config) `zenml.pipelines.base_pipeline_test.test_to_from_config`\(_equal\_pipelines_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline_test.test_to_from_config)

### zenml.pipelines.data\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.data_pipeline)

Pipeline to create data sources _class_ `zenml.pipelines.data_pipeline.DataPipeline`\(_name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_, _\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline)

Bases: [`zenml.pipelines.base_pipeline.BasePipeline`](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

DataPipeline definition to create datasources.

A DataPipeline is used to create datasources in ZenML. Each data pipeline creates a snapshot of the datasource in time. All datasources are consumed by different ZenML pipelines like the TrainingPipeline. `PIPELINE_TYPE` _= 'data'_[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline.PIPELINE_TYPE) `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline.get_tfx_component_list)

Creates a data pipeline out of TFX components.

A data pipeline is used to ingest data from a configured source, e.g. local files or cloud storage. In addition, a schema and statistics are also computed immediately afterwards for the processed data points.Parameters

**config** – Dict. Contains a ZenML configuration used to build the data pipeline.Returns

A list of TFX components making up the data pipeline. `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline.steps_completed)

Returns True if all steps complete, else raises exception `view_schema`\(\)[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline.view_schema)

View schema of data flowing in pipeline. `view_statistics`\(_magic: bool = False_, _port: int = 0_\)[¶](zenml.pipelines.md#zenml.pipelines.data_pipeline.DataPipeline.view_statistics)

View statistics for data pipeline in HTML.Parameters

* **magic** \(_bool_\) – Creates HTML page if False, else
* **a notebook cell.** \(_creates_\) –
* **port** \(_int_\) – Port at which to launch the statistics facet.

### zenml.pipelines.deploy\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.deploy_pipeline)

 _class_ `zenml.pipelines.deploy_pipeline.DeploymentPipeline`\(_model\_uri: str_, _name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_\)[¶](zenml.pipelines.md#zenml.pipelines.deploy_pipeline.DeploymentPipeline)

Bases: [`zenml.pipelines.base_pipeline.BasePipeline`](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

BatchInferencePipeline definition to run batch inference pipelines.

A BatchInferencePipeline is used to run an inference based on a TrainingPipeline. `PIPELINE_TYPE` _= 'deploy'_[¶](zenml.pipelines.md#zenml.pipelines.deploy_pipeline.DeploymentPipeline.PIPELINE_TYPE) `add_deployment`\(_deployment\_step:_ [_zenml.steps.deployer.base\_deployer.BaseDeployerStep_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#zenml.steps.deployer.base_deployer.BaseDeployerStep)\)[¶](zenml.pipelines.md#zenml.pipelines.deploy_pipeline.DeploymentPipeline.add_deployment) `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.deploy_pipeline.DeploymentPipeline.get_tfx_component_list)

Creates an inference pipeline out of TFX components.

A inference pipeline is used to run a batch of data through a ML model via the BulkInferrer TFX component.Parameters

**config** – Dict. Contains a ZenML configuration used to build the data pipeline.Returns

A list of TFX components making up the data pipeline. `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.deploy_pipeline.DeploymentPipeline.steps_completed)

Returns True if all steps complete, else raises exception

### zenml.pipelines.infer\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.infer_pipeline)

 _class_ `zenml.pipelines.infer_pipeline.BatchInferencePipeline`\(_model\_uri: str_, _name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_\)[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline)

Bases: [`zenml.pipelines.base_pipeline.BasePipeline`](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

BatchInferencePipeline definition to run batch inference pipelines.

A BatchInferencePipeline is used to run an inference based on a TrainingPipeline. `PIPELINE_TYPE` _= 'infer'_[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.PIPELINE_TYPE) `add_infer_step`\(_infer\_step:_ [_zenml.steps.inferrer.base\_inferrer\_step.BaseInferrer_](zenml.steps/zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer)\)[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.add_infer_step) `get_predictions`\(_sample\_size: int = 100000_\)[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.get_predictions)

Samples prediction data as a pandas DataFrame.Parameters

**sample\_size** – \# of rows to sample. `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.get_tfx_component_list)

Creates an inference pipeline out of TFX components.

A inference pipeline is used to run a batch of data through a ML model via the BulkInferrer TFX component.Parameters

**config** – Dict. Contains a ZenML configuration used to build the data pipeline.Returns

A list of TFX components making up the data pipeline. `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.steps_completed)

Returns True if all steps complete, else raises exception `view_schema`\(\)[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.view_schema)

View schema of data flowing in pipeline. `view_statistics`\(_magic: bool = False_, _port: int = 0_\)[¶](zenml.pipelines.md#zenml.pipelines.infer_pipeline.BatchInferencePipeline.view_statistics)

View statistics for infer pipeline in HTML.Parameters

* **magic** \(_bool_\) – Creates HTML page if False, else
* **a notebook cell.** \(_creates_\) –
* **port** \(_int_\) – Port at which to launch the statistics facet.

### zenml.pipelines.nlp\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.nlp_pipeline)

ZenML NLP Pipeline Prototype. _class_ `zenml.pipelines.nlp_pipeline.NLPPipeline`\(_name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_, _\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline)

Bases: [`zenml.pipelines.base_pipeline.BasePipeline`](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline) `PIPELINE_TYPE` _= 'nlp'_[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.PIPELINE_TYPE) `add_split`\(_split\_step:_ [_zenml.steps.split.base\_split\_step.BaseSplit_](zenml.steps/zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.add_split) `add_tokenizer`\(_tokenizer\_step:_ [_zenml.steps.tokenizer.base\_tokenizer.BaseTokenizer_](zenml.steps/zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer)\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.add_tokenizer) `add_trainer`\(_trainer\_step:_ [_zenml.steps.trainer.base\_trainer.BaseTrainerStep_](zenml.steps/zenml.steps.trainer/#zenml.steps.trainer.base_trainer.BaseTrainerStep)\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.add_trainer) `get_model_uri`\(\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.get_model_uri)

Gets model artifact. `get_schema_uri`\(\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.get_schema_uri)

Gets transform artifact. `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.get_tfx_component_list)

Builds the NLP pipeline as a series of TFX components.Parameters

**config** – A ZenML configuration in dictionary format.Returns

A chronological list of TFX components making up the NLP

pipeline.

 `get_tokenizer_uri`\(\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.get_tokenizer_uri)

Gets transform artifact. `predict_sentence`\(_sequence: Union\[str, List\[str\]\]_\)[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.predict_sentence)

Call operator for local inference method `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.nlp_pipeline.NLPPipeline.steps_completed)

Returns True if all steps complete, else raises exception

### zenml.pipelines.training\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.training_pipeline)

Training pipeline step to create a pipeline that trains on data. _class_ `zenml.pipelines.training_pipeline.TrainingPipeline`\(_name: str = None_, _enable\_cache: Optional\[bool\] = True_, _steps\_dict: Dict\[str,_ [_zenml.steps.base\_step.BaseStep_](zenml.steps/#zenml.steps.base_step.BaseStep)_\] = None_, _backend:_ [_zenml.backends.orchestrator.base.orchestrator\_base\_backend.OrchestratorBaseBackend_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend) _= None_, _metadata\_store: Optional\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\] = None_, _artifact\_store: Optional\[_[_zenml.repo.artifact\_store.ArtifactStore_](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)_\] = None_, _datasource: Optional\[_[_zenml.datasources.base\_datasource.BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)_\] = None_, _pipeline\_name: Optional\[str\] = None_, _\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline)

Bases: [`zenml.pipelines.base_pipeline.BasePipeline`](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

Definition of the Training Pipeline class.

TrainingPipeline is a general-purpose training pipeline for most ML training runs. One pipeline runs one experiment on a single datasource. `PIPELINE_TYPE` _= 'training'_[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.PIPELINE_TYPE) `add_deployment`\(_deployment\_step:_ [_zenml.steps.deployer.base\_deployer.BaseDeployerStep_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.deployer.html#zenml.steps.deployer.base_deployer.BaseDeployerStep)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_deployment) `add_evaluator`\(_evaluator\_step:_ [_zenml.steps.evaluator.base\_evaluator.BaseEvaluatorStep_](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html#zenml.steps.evaluator.base_evaluator.BaseEvaluatorStep)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_evaluator) `add_preprocesser`\(_preprocessor\_step:_ [_zenml.steps.preprocesser.base\_preprocesser.BasePreprocesserStep_](zenml.steps/zenml.steps.preprocesser/#zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_preprocesser) `add_sequencer`\(_sequencer\_step:_ [_zenml.steps.sequencer.base\_sequencer.BaseSequencerStep_](zenml.steps/zenml.steps.sequencer/#zenml.steps.sequencer.base_sequencer.BaseSequencerStep)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_sequencer) `add_split`\(_split\_step:_ [_zenml.steps.split.base\_split\_step.BaseSplit_](zenml.steps/zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_split) `add_trainer`\(_trainer\_step:_ [_zenml.steps.trainer.base\_trainer.BaseTrainerStep_](zenml.steps/zenml.steps.trainer/#zenml.steps.trainer.base_trainer.BaseTrainerStep)\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.add_trainer) `download_model`\(_out\_path: str = None_, _overwrite: bool = False_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.download_model)

Download model to out\_path `evaluate`\(_magic: bool = False_, _port: int = 0_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.evaluate)

Evaluate pipeline from the evaluator and trainer steps artifact.Parameters

* **magic** – Creates new window if False, else creates notebook cells.
* **port** – At which port to deploy jupyter notebook.

 `get_hyperparameters`\(\) → Dict[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.get_hyperparameters)

Gets all hyper-parameters of pipeline. `get_model_uri`\(\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.get_model_uri)

Gets model artifact. `get_tfx_component_list`\(_config: Dict\[str, Any\]_\) → List[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.get_tfx_component_list)

Builds the training pipeline as a series of TFX components.Parameters

**config** – A ZenML configuration in dictionary format.Returns

A chronological list of TFX components making up the training

pipeline.

 `sample_transformed_data`\(_split\_name: str = 'eval'_, _sample\_size: int = 100000_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.sample_transformed_data)

Samples transformed data as a pandas DataFrame.Parameters

* **split\_name** – name of split to see
* **sample\_size** – \# of rows to sample.

 `steps_completed`\(\) → bool[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.steps_completed)

Returns True if all steps complete, else raises exception `view_anomalies`\(_split\_name='eval'_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.view_anomalies)

View schema of data flowing in pipeline.Parameters

**split\_name** – name of split to detect anomalies on `view_schema`\(\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.view_schema)

View schema of data flowing in pipeline. `view_statistics`\(_magic: bool = False_, _port: int = 0_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline.TrainingPipeline.view_statistics)

View statistics for training pipeline in HTML.Parameters

* **magic** \(_bool_\) – Creates HTML page if False, else
* **a notebook cell.** \(_creates_\) –
* **port** \(_int_\) – Port at which to launch the statistics facet.

### zenml.pipelines.training\_pipeline\_test module[¶](zenml.pipelines.md#module-zenml.pipelines.training_pipeline_test)

 `zenml.pipelines.training_pipeline_test.test_view_anomalies`\(_repo_\)[¶](zenml.pipelines.md#zenml.pipelines.training_pipeline_test.test_view_anomalies)

### zenml.pipelines.utils module[¶](zenml.pipelines.md#module-zenml.pipelines.utils)

 `zenml.pipelines.utils.generate_unique_name`\(_base\_name_\)[¶](zenml.pipelines.md#zenml.pipelines.utils.generate_unique_name)Parameters

**base\_name** – `zenml.pipelines.utils.parse_yaml_beam_args`\(_pipeline\_args_\)[¶](zenml.pipelines.md#zenml.pipelines.utils.parse_yaml_beam_args)

Converts yaml beam args to list of args TFX acceptsParameters

**pipeline\_args** – dict specified in the config.ymlReturns

list of strings, where each string is a beam argument `zenml.pipelines.utils.prepare_sdist`\(\)[¶](zenml.pipelines.md#zenml.pipelines.utils.prepare_sdist)

Refer to the README.md in the docs folder `zenml.pipelines.utils.sanitize_name_for_ai_platform`\(_name: str_\)[¶](zenml.pipelines.md#zenml.pipelines.utils.sanitize_name_for_ai_platform)Parameters

**name** \(_str_\) –

### Module contents[¶](zenml.pipelines.md#module-zenml.pipelines)

 [Back to top](zenml.pipelines.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


