# Standards

&lt;!DOCTYPE html&gt;

zenml.standards package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.standards.md)
  * * [zenml.standards package](zenml.standards.md)
      * [Submodules](zenml.standards.md#submodules)
      * [zenml.standards.standard\_keys module](zenml.standards.md#module-zenml.standards.standard_keys)
      * [Module contents](zenml.standards.md#module-zenml.standards)
* [ « zenml.repo package](zenml.repo.md)
* [ zenml.steps package »](zenml.steps/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.standards.rst.txt)

## zenml.standards package[¶](zenml.standards.md#zenml-standards-package)

### Submodules[¶](zenml.standards.md#submodules)

### zenml.standards.standard\_keys module[¶](zenml.standards.md#module-zenml.standards.standard_keys)

 _class_ `zenml.standards.standard_keys.BackendKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.BackendKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ARGS` _= 'args'_[¶](zenml.standards.md#zenml.standards.standard_keys.BackendKeys.ARGS) `SOURCE` _= 'source'_[¶](zenml.standards.md#zenml.standards.standard_keys.BackendKeys.SOURCE) `TYPE` _= 'type'_[¶](zenml.standards.md#zenml.standards.standard_keys.BackendKeys.TYPE) _class_ `zenml.standards.standard_keys.ConfigKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys)

Bases: `object` _classmethod_ `get_keys`\(\)[¶](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys.get_keys) _classmethod_ `key_check`\(_\_input_\)[¶](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys.key_check)Parameters

**\_input** – _class_ `zenml.standards.standard_keys.DataSteps`[¶](zenml.standards.md#zenml.standards.standard_keys.DataSteps)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `DATA` _= 'data'_[¶](zenml.standards.md#zenml.standards.standard_keys.DataSteps.DATA) _class_ `zenml.standards.standard_keys.DatasourceKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.DatasourceKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ID` _= 'id'_[¶](zenml.standards.md#zenml.standards.standard_keys.DatasourceKeys.ID) `NAME` _= 'name'_[¶](zenml.standards.md#zenml.standards.standard_keys.DatasourceKeys.NAME) `SOURCE` _= 'source'_[¶](zenml.standards.md#zenml.standards.standard_keys.DatasourceKeys.SOURCE) _class_ `zenml.standards.standard_keys.DefaultKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.DefaultKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `BOOLEAN` _= 'boolean'_[¶](zenml.standards.md#zenml.standards.standard_keys.DefaultKeys.BOOLEAN) `FLOAT` _= 'float'_[¶](zenml.standards.md#zenml.standards.standard_keys.DefaultKeys.FLOAT) `INTEGER` _= 'integer'_[¶](zenml.standards.md#zenml.standards.standard_keys.DefaultKeys.INTEGER) `STRING` _= 'string'_[¶](zenml.standards.md#zenml.standards.standard_keys.DefaultKeys.STRING) _class_ `zenml.standards.standard_keys.GlobalKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ARTIFACT_STORE` _= 'artifact\_store'_[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys.ARTIFACT_STORE) `BACKEND` _= 'backend'_[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys.BACKEND) `METADATA_STORE` _= 'metadata'_[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys.METADATA_STORE) `PIPELINE` _= 'pipeline'_[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys.PIPELINE) `VERSION` _= 'version'_[¶](zenml.standards.md#zenml.standards.standard_keys.GlobalKeys.VERSION) _class_ `zenml.standards.standard_keys.InferSteps`[¶](zenml.standards.md#zenml.standards.standard_keys.InferSteps)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `DATA` _= 'data'_[¶](zenml.standards.md#zenml.standards.standard_keys.InferSteps.DATA) `INFER` _= 'infer'_[¶](zenml.standards.md#zenml.standards.standard_keys.InferSteps.INFER) _class_ `zenml.standards.standard_keys.MLMetadataKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.MLMetadataKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ARGS` _= 'args'_[¶](zenml.standards.md#zenml.standards.standard_keys.MLMetadataKeys.ARGS) `TYPE` _= 'type'_[¶](zenml.standards.md#zenml.standards.standard_keys.MLMetadataKeys.TYPE) _class_ `zenml.standards.standard_keys.MethodKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.MethodKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `METHOD` _= 'method'_[¶](zenml.standards.md#zenml.standards.standard_keys.MethodKeys.METHOD) `PARAMETERS` _= 'parameters'_[¶](zenml.standards.md#zenml.standards.standard_keys.MethodKeys.PARAMETERS) _class_ `zenml.standards.standard_keys.NLPSteps`[¶](zenml.standards.md#zenml.standards.standard_keys.NLPSteps)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `DATA` _= 'data'_[¶](zenml.standards.md#zenml.standards.standard_keys.NLPSteps.DATA) `SPLIT` _= 'split'_[¶](zenml.standards.md#zenml.standards.standard_keys.NLPSteps.SPLIT) `TOKENIZER` _= 'tokenizer'_[¶](zenml.standards.md#zenml.standards.standard_keys.NLPSteps.TOKENIZER) `TRAINER` _= 'trainer'_[¶](zenml.standards.md#zenml.standards.standard_keys.NLPSteps.TRAINER) _class_ `zenml.standards.standard_keys.PipelineDetailKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineDetailKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ENABLE_CACHE` _= 'enable\_cache'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineDetailKeys.ENABLE_CACHE) `NAME` _= 'name'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineDetailKeys.NAME) `TYPE` _= 'type'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineDetailKeys.TYPE) _class_ `zenml.standards.standard_keys.PipelineKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ARGS` _= 'args'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys.ARGS) `DATASOURCE` _= 'datasource'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys.DATASOURCE) `ENABLE_CACHE` _= 'enable\_cache'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys.ENABLE_CACHE) `SOURCE` _= 'source'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys.SOURCE) `STEPS` _= 'steps'_[¶](zenml.standards.md#zenml.standards.standard_keys.PipelineKeys.STEPS) _class_ `zenml.standards.standard_keys.StepKeys`[¶](zenml.standards.md#zenml.standards.standard_keys.StepKeys)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `ARGS` _= 'args'_[¶](zenml.standards.md#zenml.standards.standard_keys.StepKeys.ARGS) `BACKEND` _= 'backend'_[¶](zenml.standards.md#zenml.standards.standard_keys.StepKeys.BACKEND) `NAME` _= 'name'_[¶](zenml.standards.md#zenml.standards.standard_keys.StepKeys.NAME) `SOURCE` _= 'source'_[¶](zenml.standards.md#zenml.standards.standard_keys.StepKeys.SOURCE) _class_ `zenml.standards.standard_keys.TrainingSteps`[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps)

Bases: [`zenml.standards.standard_keys.ConfigKeys`](zenml.standards.md#zenml.standards.standard_keys.ConfigKeys) `DATA` _= 'data'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.DATA) `DEPLOYER` _= 'deployer'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.DEPLOYER) `EVALUATOR` _= 'evaluator'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.EVALUATOR) `PREPROCESSER` _= 'preprocesser'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.PREPROCESSER) `SEQUENCER` _= 'sequencer'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.SEQUENCER) `SPLIT` _= 'split'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.SPLIT) `TRAINER` _= 'trainer'_[¶](zenml.standards.md#zenml.standards.standard_keys.TrainingSteps.TRAINER)

### Module contents[¶](zenml.standards.md#module-zenml.standards)

 [Back to top](zenml.standards.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


