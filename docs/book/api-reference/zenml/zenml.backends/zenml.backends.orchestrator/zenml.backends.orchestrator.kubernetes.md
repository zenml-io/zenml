# Kubernetes

&lt;!DOCTYPE html&gt;

zenml.backends.orchestrator.kubernetes package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.backends.orchestrator.kubernetes.md)
  * * [zenml.backends.orchestrator.kubernetes package](zenml.backends.orchestrator.kubernetes.md)
      * [Submodules](zenml.backends.orchestrator.kubernetes.md#submodules)
      * [zenml.backends.orchestrator.kubernetes.orchestrator\_kubernetes\_backend module](zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend)
      * [Module contents](zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes)
* [ « zenml.backend...](zenml.backends.orchestrator.kubeflow.md)
* [ zenml.backend... »](../zenml.backends.processing.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.backends.orchestrator.kubernetes.rst.txt)

## zenml.backends.orchestrator.kubernetes package[¶](zenml.backends.orchestrator.kubernetes.md#zenml-backends-orchestrator-kubernetes-package)

### Submodules[¶](zenml.backends.orchestrator.kubernetes.md#submodules)

### zenml.backends.orchestrator.kubernetes.orchestrator\_kubernetes\_backend module[¶](zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend)

Definition of the Kubernetes Orchestrator Backend _class_ `zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend.OrchestratorKubernetesBackend`\(_image: str = 'eu.gcr.io/maiot-zenml/zenml:base-0.3.6.1'_, _job\_prefix: str = 'zenml-'_, _extra\_labels: Dict\[str, Any\] = None_, _extra\_annotations: Dict\[str, Any\] = None_, _namespace: str = None_, _image\_pull\_policy: str = 'IfNotPresent'_, _kubernetes\_config\_path: str = '/home/hamza/.kube/config'_\)[¶](zenml.backends.orchestrator.kubernetes.md#zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend.OrchestratorKubernetesBackend)

Bases: [`zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend`](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.backends.orchestrator.base.html#zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend)

Runs pipeline on a Kubernetes cluster.

This orchestrator creates a .tar.gz of the current ZenML repository, sends it over to the artifact store, then launches a job in a Kubernetes cluster taken from your environment or specified via a passed-on kubectl config.Parameters

* **image** – the Docker Image to be used for this ZenML pipeline
* **job\_prefix** – a custom prefix for your Jobs in Kubernetes \(default: ‘zenml-‘\)
* **extra\_labels** – additional labels for your Jobs in Kubernetes
* **extra\_annotations** – additional annotations for your Jobs in Kubernetes
* **namespace** – a custom Kubernetes namespace for this pipeline \(default: ‘default’\)
* **image\_pull\_policy** – Kubernetes image pull policy. One of \[‘Always’, ‘Never’, ‘IfNotPresent’\]. \(default: ‘IfNotPresent’\)
* **kubernetes\_config\_path** – Path to your Kubernetes cluster connection
* **config.** – \(default: ‘~/.kube/config’

 `create_job_object`\(_config_\)[¶](zenml.backends.orchestrator.kubernetes.md#zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend.OrchestratorKubernetesBackend.create_job_object) `launch_job`\(_config: Dict\[str, Any\]_\)[¶](zenml.backends.orchestrator.kubernetes.md#zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend.OrchestratorKubernetesBackend.launch_job) `run`\(_config: Dict\[str, Any\]_\)[¶](zenml.backends.orchestrator.kubernetes.md#zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend.OrchestratorKubernetesBackend.run)

This run function essentially calls an underlying TFX orchestrator run. However it is meant as a higher level abstraction with some opinionated decisions taken.Parameters

**config** – a ZenML config dict

### Module contents[¶](zenml.backends.orchestrator.kubernetes.md#module-zenml.backends.orchestrator.kubernetes)

 [Back to top](zenml.backends.orchestrator.kubernetes.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


