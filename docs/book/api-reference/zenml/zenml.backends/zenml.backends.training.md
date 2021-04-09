# Training

&lt;!DOCTYPE html&gt;

zenml.backends.training package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.backends.training.md)
  * * [zenml.backends.training package](zenml.backends.training.md)
      * [Submodules](zenml.backends.training.md#submodules)
      * [zenml.backends.training.training\_base\_backend module](zenml.backends.training.md#module-zenml.backends.training.training_base_backend)
      * [zenml.backends.training.training\_gcaip\_backend module](zenml.backends.training.md#module-zenml.backends.training.training_gcaip_backend)
      * [Module contents](zenml.backends.training.md#module-zenml.backends.training)
* [ « zenml.backend...](zenml.backends.processing.md)
* [ zenml.cli package »](../zenml.cli.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.backends.training.rst.txt)

## zenml.backends.training package[¶](zenml.backends.training.md#zenml-backends-training-package)

### Submodules[¶](zenml.backends.training.md#submodules)

### zenml.backends.training.training\_base\_backend module[¶](zenml.backends.training.md#module-zenml.backends.training.training_base_backend)

Definition of the base Training Backend _class_ `zenml.backends.training.training_base_backend.TrainingBaseBackend`\(_\*\*kwargs_\)[¶](zenml.backends.training.md#zenml.backends.training.training_base_backend.TrainingBaseBackend)

Bases: [`zenml.backends.base_backend.BaseBackend`](./#zenml.backends.base_backend.BaseBackend)

Base class for all base Training ZenML backends.

Every ZenML pipeline runs in backends.

A training backend can be used to efficiently train a machine learning model on large amounts of data. Since most common machine learning models leverage mainly linear algebra operations under the hood, they can potentially benefit a lot from dedicated training hardware like Graphics Processing Units \(GPUs\) or application-specific integrated circuits \(ASICs\). `BACKEND_TYPE` _= 'training'_[¶](zenml.backends.training.md#zenml.backends.training.training_base_backend.TrainingBaseBackend.BACKEND_TYPE) `get_custom_config`\(\)[¶](zenml.backends.training.md#zenml.backends.training.training_base_backend.TrainingBaseBackend.get_custom_config)

Return a dict to be passed as a custom\_config to the Trainer. `get_executor_spec`\(\)[¶](zenml.backends.training.md#zenml.backends.training.training_base_backend.TrainingBaseBackend.get_executor_spec)

Return a TFX Executor spec for the Trainer Component.

### zenml.backends.training.training\_gcaip\_backend module[¶](zenml.backends.training.md#module-zenml.backends.training.training_gcaip_backend)

Definition of the GCAIP Training Backend _class_ `zenml.backends.training.training_gcaip_backend.SingleGPUTrainingGCAIPBackend`\(_project: str_, _job\_dir: str_, _gpu\_type: str = 'K80'_, _machine\_type: str = 'n1-standard-4'_, _image: str = 'eu.gcr.io/maiot-zenml/zenml:cuda-0.3.6.1'_, _job\_name: str = 'train\_1617886391'_, _region: str = 'europe-west1'_, _python\_version: str = '3.7'_, _max\_running\_time: int = 7200_\)[¶](zenml.backends.training.md#zenml.backends.training.training_gcaip_backend.SingleGPUTrainingGCAIPBackend)

Bases: [`zenml.backends.training.training_base_backend.TrainingBaseBackend`](zenml.backends.training.md#zenml.backends.training.training_base_backend.TrainingBaseBackend)

Runs a TrainerStep on Google Cloud AI Platform.

A training backend can be used to efficiently train a machine learning model on large amounts of data. This triggers a Training job on the Google Cloud AI Platform service: [https://cloud.google.com/ai-platform](https://cloud.google.com/ai-platform).

This backend is meant for a training job with a single GPU only. The user has a choice of three GPUs, specified in the GCPGPUTypes Enum. `get_custom_config`\(\)[¶](zenml.backends.training.md#zenml.backends.training.training_gcaip_backend.SingleGPUTrainingGCAIPBackend.get_custom_config)

Return a dict to be passed as a custom\_config to the Trainer. `get_executor_spec`\(\)[¶](zenml.backends.training.md#zenml.backends.training.training_gcaip_backend.SingleGPUTrainingGCAIPBackend.get_executor_spec)

Return a TFX Executor spec for the Trainer Component.

### Module contents[¶](zenml.backends.training.md#module-zenml.backends.training)

 [Back to top](zenml.backends.training.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


