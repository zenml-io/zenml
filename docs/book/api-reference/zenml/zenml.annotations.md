# Annotations

&lt;!DOCTYPE html&gt;

zenml.annotations package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.annotations.md)
  * * [zenml.annotations package](zenml.annotations.md)
      * [Submodules](zenml.annotations.md#submodules)
      * [zenml.annotations.artifact\_annotations module](zenml.annotations.md#module-zenml.annotations.artifact_annotations)
      * [zenml.annotations.base\_annotations module](zenml.annotations.md#module-zenml.annotations.base_annotations)
      * [zenml.annotations.param\_annotations module](zenml.annotations.md#module-zenml.annotations.param_annotations)
      * [zenml.annotations.step\_annotations module](zenml.annotations.md#module-zenml.annotations.step_annotations)
      * [Module contents](zenml.annotations.md#module-zenml.annotations)
* [ « zenml package](./)
* [ zenml.artifac... »](zenml.artifact_stores.md)
*  [Source](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/_sources/zenml.annotations.rst.txt)

## zenml.annotations package[¶](zenml.annotations.md#zenml-annotations-package)

### Submodules[¶](zenml.annotations.md#submodules)

### zenml.annotations.artifact\_annotations module[¶](zenml.annotations.md#module-zenml.annotations.artifact_annotations)

 _class_ zenml.annotations.artifact\_annotations.Input\(_object\_type_, _\_init\_via\_getitem=False_\)[¶](zenml.annotations.md#zenml.annotations.artifact_annotations.Input)

Bases: [`zenml.annotations.base_annotations.BaseAnnotation`](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation) VALID\_TYPES _= \[&lt;class 'zenml.artifacts.base\_artifact.BaseArtifact'&gt;\]_[¶](zenml.annotations.md#zenml.annotations.artifact_annotations.Input.VALID_TYPES) _class_ zenml.annotations.artifact\_annotations.Output\(_object\_type_, _\_init\_via\_getitem=False_\)[¶](zenml.annotations.md#zenml.annotations.artifact_annotations.Output)

Bases: [`zenml.annotations.base_annotations.BaseAnnotation`](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation) VALID\_TYPES _= \[&lt;class 'zenml.artifacts.base\_artifact.BaseArtifact'&gt;\]_[¶](zenml.annotations.md#zenml.annotations.artifact_annotations.Output.VALID_TYPES)

### zenml.annotations.base\_annotations module[¶](zenml.annotations.md#module-zenml.annotations.base_annotations)

The implementation of the GenericType and GenericMeta class below is inspired by the implementation by the Tensorflow Extended team, which can be found here:

[https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/annotations.py](https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/annotations.py)

The list of changes to improve the interaction with ZenML:

* The main classes are merged into a single class which serves as the base

class to be extended - A class variable is added to be utilized while checking the type of T - A few more classes are created on top of artifacts and primitives in order to use the same paradigm with steps and datasources as well _class_ zenml.annotations.base\_annotations.BaseAnnotation\(_object\_type_, _\_init\_via\_getitem=False_\)[¶](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation)

Bases: `object`

A main generic class which will be used as the base for annotations VALID\_TYPES _= None_[¶](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation.VALID_TYPES) _class_ zenml.annotations.base\_annotations.BaseAnnotationMeta[¶](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotationMeta)

Bases: `type`

The Metaclass for the annotations in ZenML. It defines a \_\_get\_item\_\_ method which in return class the \_\_generic\_getitem of the main class with the same param

### zenml.annotations.param\_annotations module[¶](zenml.annotations.md#module-zenml.annotations.param_annotations)

 _class_ zenml.annotations.param\_annotations.Param\(_object\_type_, _\_init\_via\_getitem=False_\)[¶](zenml.annotations.md#zenml.annotations.param_annotations.Param)

Bases: [`zenml.annotations.base_annotations.BaseAnnotation`](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation) VALID\_TYPES _= \[&lt;class 'int'&gt;, &lt;class 'float'&gt;, &lt;class 'str'&gt;, &lt;class 'bool'&gt;\]_[¶](zenml.annotations.md#zenml.annotations.param_annotations.Param.VALID_TYPES)

### zenml.annotations.step\_annotations module[¶](zenml.annotations.md#module-zenml.annotations.step_annotations)

 _class_ zenml.annotations.step\_annotations.Step\(_object\_type_, _\_init\_via\_getitem=False_\)[¶](zenml.annotations.md#zenml.annotations.step_annotations.Step)

Bases: [`zenml.annotations.base_annotations.BaseAnnotation`](zenml.annotations.md#zenml.annotations.base_annotations.BaseAnnotation) VALID\_TYPES _= \[&lt;class 'zenml.steps.base\_step.BaseStep'&gt;\]_[¶](zenml.annotations.md#zenml.annotations.step_annotations.Step.VALID_TYPES)

### Module contents[¶](zenml.annotations.md#module-zenml.annotations)

 [Back to top](zenml.annotations.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


