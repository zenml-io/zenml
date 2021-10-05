# Orchestrators

&lt;!DOCTYPE html&gt;

zenml.orchestrators package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.orchestrators package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.orchestrators.base\_orchestrator module](./#module-zenml.orchestrators.base_orchestrator)
      * [Module contents](./#module-zenml.orchestrators)
* [ « zenml.metadat...](../zenml.metadata.md)
* [ zenml.orchest... »](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html)
*  [Source](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/_sources/zenml.orchestrators.rst.txt)

## zenml.orchestrators package[¶](./#zenml-orchestrators-package)

### Subpackages[¶](./#subpackages)

* [zenml.orchestrators.airflow package](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html)
  * [Submodules](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html#submodules)
  * [zenml.orchestrators.airflow.airflow\_component module](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html#zenml-orchestrators-airflow-airflow-component-module)
  * [zenml.orchestrators.airflow.airflow\_dag\_runner module](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html#zenml-orchestrators-airflow-airflow-dag-runner-module)
  * [zenml.orchestrators.airflow.airflow\_orchestrator module](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html#zenml-orchestrators-airflow-airflow-orchestrator-module)
  * [Module contents](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/zenml.orchestrators.airflow.html#module-zenml.orchestrators.airflow)
* [zenml.orchestrators.local package](zenml.orchestrators.local.md)
  * [Submodules](zenml.orchestrators.local.md#submodules)
  * [zenml.orchestrators.local.local\_orchestrator module](zenml.orchestrators.local.md#module-zenml.orchestrators.local.local_orchestrator)
  * [Module contents](zenml.orchestrators.local.md#module-zenml.orchestrators.local)

### Submodules[¶](./#submodules)

### zenml.orchestrators.base\_orchestrator module[¶](./#module-zenml.orchestrators.base_orchestrator)

 _class_ zenml.orchestrators.base\_orchestrator.BaseOrchestrator\(_\*_, _uuid: uuid.UUID = None_\)[¶](./#zenml.orchestrators.base_orchestrator.BaseOrchestrator)

Bases: [`zenml.core.base_component.BaseComponent`](../zenml.core.md#zenml.core.base_component.BaseComponent) _class_ Config[¶](./#zenml.orchestrators.base_orchestrator.BaseOrchestrator.Config)

Bases: `object`

Configuration of settings. env\_prefix _= 'zenml\_orchestrator\_'_[¶](./#zenml.orchestrators.base_orchestrator.BaseOrchestrator.Config.env_prefix) get\_serialization\_dir\(\)[¶](./#zenml.orchestrators.base_orchestrator.BaseOrchestrator.get_serialization_dir)

Gets the local path where artifacts are stored. _abstract_ run\(_zenml\_pipeline_, _\*\*kwargs_\)[¶](./#zenml.orchestrators.base_orchestrator.BaseOrchestrator.run)

### Module contents[¶](./#module-zenml.orchestrators)

 [Back to top](./)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


