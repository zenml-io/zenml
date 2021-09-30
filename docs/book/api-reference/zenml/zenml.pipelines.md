# Pipelines

&lt;!DOCTYPE html&gt;

zenml.pipelines package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.pipelines.md)
  * * [zenml.pipelines package](zenml.pipelines.md)
      * [Submodules](zenml.pipelines.md#submodules)
      * [zenml.pipelines.base\_pipeline module](zenml.pipelines.md#module-zenml.pipelines.base_pipeline)
      * [zenml.pipelines.pipeline\_decorator module](zenml.pipelines.md#module-zenml.pipelines.pipeline_decorator)
      * [Module contents](zenml.pipelines.md#module-zenml.pipelines)
* [ « zenml.orchest...](zenml.orchestrators/zenml.orchestrators.local.md)
* [ zenml.stacks package »](zenml.stacks.md)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.pipelines.rst.txt)

## zenml.pipelines package[¶](zenml.pipelines.md#zenml-pipelines-package)

### Submodules[¶](zenml.pipelines.md#submodules)

### zenml.pipelines.base\_pipeline module[¶](zenml.pipelines.md#module-zenml.pipelines.base_pipeline)

 _class_ zenml.pipelines.base\_pipeline.BasePipeline\(_\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)

Bases: `object` INPUT\_SPEC _= {}_[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.INPUT_SPEC) STEP\_SPEC _= {}_[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.STEP_SPEC) _abstract_ connect\(_\*args_, _\*\*kwargs_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.connect) _classmethod_ get\_executable\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.get_executable) _property_ inputs[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.inputs) run\(\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.run) _property_ stack[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.stack) _property_ steps[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline.steps) _class_ zenml.pipelines.base\_pipeline.BasePipelineMeta\(_name_, _bases_, _dct_\)[¶](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipelineMeta)

Bases: `type`

### zenml.pipelines.pipeline\_decorator module[¶](zenml.pipelines.md#module-zenml.pipelines.pipeline_decorator)

 zenml.pipelines.pipeline\_decorator.pipeline\(_name: Optional\[str\] = None_\)[¶](zenml.pipelines.md#zenml.pipelines.pipeline_decorator.pipeline)

Outer decorator function for the creation of a ZenML pipeline

In order to be able work with parameters such as “name”, it features a nested decorator structure.Parameters

**name** – str, the given name for the pipelineReturns

the inner decorator which creates the pipeline class based on the ZenML BasePipeline

### Module contents[¶](zenml.pipelines.md#module-zenml.pipelines)

 [Back to top](zenml.pipelines.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


