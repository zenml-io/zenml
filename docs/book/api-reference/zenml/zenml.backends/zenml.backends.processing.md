# Processing

&lt;!DOCTYPE html&gt;

zenml.backends.processing package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.backends.processing.md)
  * * [zenml.backends.processing package](zenml.backends.processing.md)
      * [Submodules](zenml.backends.processing.md#submodules)
      * [zenml.backends.processing.processing\_base\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_base_backend)
      * [zenml.backends.processing.processing\_dataflow\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_dataflow_backend)
      * [zenml.backends.processing.processing\_spark\_backend module](zenml.backends.processing.md#module-zenml.backends.processing.processing_spark_backend)
      * [Module contents](zenml.backends.processing.md#module-zenml.backends.processing)
* [ « zenml.backend...](zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md)
* [ zenml.backend... »](zenml.backends.training.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.backends.processing.rst.txt)

## zenml.backends.processing package[¶](zenml.backends.processing.md#zenml-backends-processing-package)

### Submodules[¶](zenml.backends.processing.md#submodules)

### zenml.backends.processing.processing\_base\_backend module[¶](zenml.backends.processing.md#module-zenml.backends.processing.processing_base_backend)

Definition of the data Processing Backend _class_ `zenml.backends.processing.processing_base_backend.ProcessingBaseBackend`\(_\*\*kwargs_\)[¶](zenml.backends.processing.md#zenml.backends.processing.processing_base_backend.ProcessingBaseBackend)

Bases: [`zenml.backends.base_backend.BaseBackend`](./#zenml.backends.base_backend.BaseBackend)

Use this class to run a ZenML pipeline locally.

Every ZenML pipeline runs in backends.

A dedicated processing backend can be used to efficiently process large amounts of incoming data in parallel, potentially distributed across multiple machines. This can happen on local processing backends as well as cloud-based variants like Google Cloud Dataflow. More powerful machines with higher core counts and clock speeds can be leveraged to increase processing throughput significantly. `BACKEND_TYPE` _= 'processing'_[¶](zenml.backends.processing.md#zenml.backends.processing.processing_base_backend.ProcessingBaseBackend.BACKEND_TYPE) `get_beam_args`\(_pipeline\_name: str = None_, _pipeline\_root: str = None_\) → Optional\[List\[str\]\][¶](zenml.backends.processing.md#zenml.backends.processing.processing_base_backend.ProcessingBaseBackend.get_beam_args)

Returns a list of beam args for the pipeline.Parameters

* **pipeline\_name** – Name of the pipeline.
* **pipeline\_root** – Root dir of pipeline.

### zenml.backends.processing.processing\_dataflow\_backend module[¶](zenml.backends.processing.md#module-zenml.backends.processing.processing_dataflow_backend)

Definition of the DataFlow Processing Backend _class_ `zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend`\(_project: str_, _staging\_location: str = None_, _temp\_location: str = None_, _region: str = 'europe-west1'_, _job\_name: str = 'zen\_1617886389'_, _image: str = 'eu.gcr.io/maiot-zenml/zenml:dataflow-0.3.6.1'_, _machine\_type: str = 'n1-standard-4'_, _num\_workers: int = 4_, _max\_num\_workers: int = 10_, _disk\_size\_gb: int = 50_, _autoscaling\_algorithm: str = 'THROUGHPUT\_BASED'_\)[¶](zenml.backends.processing.md#zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend)

Bases: [`zenml.backends.processing.processing_base_backend.ProcessingBaseBackend`](zenml.backends.processing.md#zenml.backends.processing.processing_base_backend.ProcessingBaseBackend)

Use this to run a ZenML pipeline on Google Dataflow.

This backend utilizes the beam v2 runner to run a custom docker image on the Dataflow job. `get_beam_args`\(_pipeline\_name: str = None_, _pipeline\_root: str = None_\) → Optional\[List\[str\]\][¶](zenml.backends.processing.md#zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend.get_beam_args)

Returns a list of beam args for the pipeline.Parameters

* **pipeline\_name** – Name of the pipeline.
* **pipeline\_root** – Root dir of pipeline.

### zenml.backends.processing.processing\_spark\_backend module[¶](zenml.backends.processing.md#module-zenml.backends.processing.processing_spark_backend)

Definition of the Spark Processing Backend _class_ `zenml.backends.processing.processing_spark_backend.ProcessingSparkBackend`\(_\*\*kwargs_\)[¶](zenml.backends.processing.md#zenml.backends.processing.processing_spark_backend.ProcessingSparkBackend)

Bases: [`zenml.backends.processing.processing_base_backend.ProcessingBaseBackend`](zenml.backends.processing.md#zenml.backends.processing.processing_base_backend.ProcessingBaseBackend)

Use this to run pipelines on Apache Spark.

A dedicated processing backend can be used to efficiently process large amounts of incoming data in parallel, potentially distributed across multiple machines. This can happen on base processing backends as well as cloud-based variants like Google Cloud Dataflow. More powerful machines with higher core counts and clock speeds can be leveraged to increase processing throughput significantly.

This backend is not implemented yet.

### Module contents[¶](zenml.backends.processing.md#module-zenml.backends.processing)

 [Back to top](zenml.backends.processing.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


