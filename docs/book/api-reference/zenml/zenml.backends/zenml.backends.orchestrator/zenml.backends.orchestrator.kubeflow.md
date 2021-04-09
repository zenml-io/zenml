# Kubeflow

&lt;!DOCTYPE html&gt;

zenml.backends.orchestrator.kubeflow package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.backends.orchestrator.kubeflow.md)
  * * [zenml.backends.orchestrator.kubeflow package](zenml.backends.orchestrator.kubeflow.md)
      * [Submodules](zenml.backends.orchestrator.kubeflow.md#submodules)
      * [zenml.backends.orchestrator.kubeflow.orchestrator\_kubeflow\_backend module](zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend)
      * [Module contents](zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow)
* [ « zenml.backend...](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.gcp.html)
* [ zenml.backend... »](zenml.backends.orchestrator.kubernetes.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.backends.orchestrator.kubeflow.rst.txt)

## zenml.backends.orchestrator.kubeflow package[¶](zenml.backends.orchestrator.kubeflow.md#zenml-backends-orchestrator-kubeflow-package)

### Submodules[¶](zenml.backends.orchestrator.kubeflow.md#submodules)

### zenml.backends.orchestrator.kubeflow.orchestrator\_kubeflow\_backend module[¶](zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend)

Definition of the Kubeflow Orchestrator Backend _class_ `zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend.OrchestratorKubeFlowBackend`\(_image: str = None_, _\*\*kwargs_\)[¶](zenml.backends.orchestrator.kubeflow.md#zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend.OrchestratorKubeFlowBackend)

Bases: [`zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend`](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend)

Runs a ZenML pipeline on a Kubeflow cluster.

This backend is not implemented yet. `run`\(_tfx\_pipeline: tfx.orchestration.pipeline.Pipeline_\)[¶](zenml.backends.orchestrator.kubeflow.md#zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend.OrchestratorKubeFlowBackend.run)

This run function essentially calls an underlying TFX orchestrator run. However it is meant as a higher level abstraction with some opinionated decisions taken.Parameters

**config** – a ZenML config dict

### Module contents[¶](zenml.backends.orchestrator.kubeflow.md#module-zenml.backends.orchestrator.kubeflow)

 [Back to top](zenml.backends.orchestrator.kubeflow.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


