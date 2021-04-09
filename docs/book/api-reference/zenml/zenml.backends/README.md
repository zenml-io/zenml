# Backends

&lt;!DOCTYPE html&gt;

zenml.backends package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.backends package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.backends.base\_backend module](./#module-zenml.backends.base_backend)
      * [zenml.backends.base\_backend\_test module](./#module-zenml.backends.base_backend_test)
      * [Module contents](./#module-zenml.backends)
* [ « zenml package](../)
* [ zenml.backend... »](zenml.backends.orchestrator/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.backends.rst.txt)

## zenml.backends package[¶](./#zenml-backends-package)

### Subpackages[¶](./#subpackages)

* [zenml.backends.orchestrator package](zenml.backends.orchestrator/)
  * [Subpackages](zenml.backends.orchestrator/#subpackages)
    * [zenml.backends.orchestrator.aws package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.aws.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.aws.html#submodules)
      * [zenml.backends.orchestrator.aws.orchestrator\_aws\_backend module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.aws.html#module-zenml.backends.orchestrator.aws.orchestrator_aws_backend)
      * [zenml.backends.orchestrator.aws.utils module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.aws.html#module-zenml.backends.orchestrator.aws.utils)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.aws.html#module-zenml.backends.orchestrator.aws)
    * [zenml.backends.orchestrator.base package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#submodules)
      * [zenml.backends.orchestrator.base.orchestrator\_base\_backend module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#module-zenml.backends.orchestrator.base.orchestrator_base_backend)
      * [zenml.backends.orchestrator.base.zenml\_local\_orchestrator module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#module-zenml.backends.orchestrator.base.zenml_local_orchestrator)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#module-zenml.backends.orchestrator.base)
    * [zenml.backends.orchestrator.beam package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.beam.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.beam.html#submodules)
      * [zenml.backends.orchestrator.beam.orchestrator\_beam\_backend module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.beam.html#zenml-backends-orchestrator-beam-orchestrator-beam-backend-module)
      * [zenml.backends.orchestrator.beam.zenml\_beam\_orchestrator module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.beam.html#zenml-backends-orchestrator-beam-zenml-beam-orchestrator-module)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.beam.html#module-zenml.backends.orchestrator.beam)
    * [zenml.backends.orchestrator.gcp package](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.gcp.html)
      * [Submodules](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.gcp.html#submodules)
      * [zenml.backends.orchestrator.gcp.orchestrator\_gcp\_backend module](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.gcp.html#module-zenml.backends.orchestrator.gcp.orchestrator_gcp_backend)
      * [Module contents](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.gcp.html#module-zenml.backends.orchestrator.gcp)
    * [zenml.backends.orchestrator.kubeflow package](zenml.backends.orchestrator/zenml.backends.orchestrator.kubeflow.md)
      * [Submodules](zenml.backends.orchestrator/zenml.backends.orchestrator.kubeflow.md#submodules)
      * [zenml.backends.orchestrator.kubeflow.orchestrator\_kubeflow\_backend module](zenml.backends.orchestrator/zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend)
      * [Module contents](zenml.backends.orchestrator/zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow)
    * [zenml.backends.orchestrator.kubernetes package](zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md)
      * [Submodules](zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md#submodules)
      * [zenml.backends.orchestrator.kubernetes.orchestrator\_kubernetes\_backend module](zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend)
      * [Module contents](zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes)
  * [Submodules](zenml.backends.orchestrator/#submodules)
  * [zenml.backends.orchestrator.entrypoint module](zenml.backends.orchestrator/#module-zenml.backends.orchestrator.entrypoint)
  * [Module contents](zenml.backends.orchestrator/#module-zenml.backends.orchestrator)
* [zenml.backends.processing package](zenml.backends.processing.md)
  * [Submodules](zenml.backends.processing.md#submodules)
  * [zenml.backends.processing.processing\_base\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_base_backend)
  * [zenml.backends.processing.processing\_dataflow\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_dataflow_backend)
  * [zenml.backends.processing.processing\_spark\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_spark_backend)
  * [Module contents](zenml.backends.processing.md#module-zenml.backends.processing)
* [zenml.backends.training package](zenml.backends.training.md)
  * [Submodules](zenml.backends.training.md#submodules)
  * [zenml.backends.training.training\_base\_backend module](zenml.backends.training.md#module-zenml.backends.training.training_base_backend)
  * [zenml.backends.training.training\_gcaip\_backend module](zenml.backends.training.md#module-zenml.backends.training.training_gcaip_backend)
  * [Module contents](zenml.backends.training.md#module-zenml.backends.training)

### Submodules[¶](./#submodules)

### zenml.backends.base\_backend module[¶](./#module-zenml.backends.base_backend)

Definition of a the base Backend _class_ `zenml.backends.base_backend.BaseBackend`\(_\*\*kwargs_\)[¶](./#zenml.backends.base_backend.BaseBackend)

Bases: `object`

Base class for all ZenML backends.

Every ZenML pipeline runs in backends that defines where and how the pipeline runs. Override this base class to define your own custom Pipeline backend.

There are three types of backends available in ZenML: Orchestration backends, processing backends and training backends. Each of them serve different purposes in different stages of the pipeline. An orchestration backend is useful for scheduling and executing the different pipeline components.

A dedicated processing backend can be used to efficiently process large amounts of incoming data in parallel, potentially distributed across multiple machines. This can happen on local processing backends as well as cloud-based variants like Google Cloud Dataflow. More powerful machines with higher core counts and clock speeds can be leveraged to increase processing throughput significantly.

A training backend can be used to efficiently train a machine learning model on large amounts of data. Since most common machine learning models leverage mainly linear algebra operations under the hood, they can potentially benefit a lot from dedicated training hardware like Graphics Processing Units \(GPUs\) or application-specific integrated circuits \(ASICs\). Again, local training backends or cloud-based training backends like Google Cloud AI Platform \(GCAIP\) with or without GPU/ASIC support can be used. `BACKEND_TYPE` _= None_[¶](./#zenml.backends.base_backend.BaseBackend.BACKEND_TYPE) _classmethod_ `from_config`\(_config: Dict_\)[¶](./#zenml.backends.base_backend.BaseBackend.from_config)

Convert from ZenML config dict to ZenML Backend object.Parameters

**config** – a ZenML config in dict-form \(probably loaded from YAML\) `to_config`\(\)[¶](./#zenml.backends.base_backend.BaseBackend.to_config)

Converts Backend to ZenML config block.

### zenml.backends.base\_backend\_test module[¶](./#module-zenml.backends.base_backend_test)

 `zenml.backends.base_backend_test.test_to_from_config`\(_equal\_backends_\)[¶](./#zenml.backends.base_backend_test.test_to_from_config)

### Module contents[¶](./#module-zenml.backends)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


