# Artifact stores

&lt;!DOCTYPE html&gt;

zenml.artifact\_stores package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.artifact_stores.md)
  * * [zenml.artifact\_stores package](zenml.artifact_stores.md)
      * [Submodules](zenml.artifact_stores.md#submodules)
      * [zenml.artifact\_stores.base\_artifact\_store module](zenml.artifact_stores.md#module-zenml.artifact_stores.base_artifact_store)
      * [zenml.artifact\_stores.gcp\_artifact\_store module](zenml.artifact_stores.md#module-zenml.artifact_stores.gcp_artifact_store)
      * [zenml.artifact\_stores.local\_artifact\_store module](zenml.artifact_stores.md#module-zenml.artifact_stores.local_artifact_store)
      * [Module contents](zenml.artifact_stores.md#module-zenml.artifact_stores)
* [ « zenml.annotat...](zenml.annotations.md)
* [ zenml.artifac... »](zenml.artifacts.md)
*  [Source](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/_sources/zenml.artifact_stores.rst.txt)

## zenml.artifact\_stores package[¶](zenml.artifact_stores.md#zenml-artifact-stores-package)

### Submodules[¶](zenml.artifact_stores.md#submodules)

### zenml.artifact\_stores.base\_artifact\_store module[¶](zenml.artifact_stores.md#module-zenml.artifact_stores.base_artifact_store)

Definition of an Artifact Store _class_ zenml.artifact\_stores.base\_artifact\_store.BaseArtifactStore\(_\*_, _uuid: uuid.UUID = None_, _path: str_\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)

Bases: [`zenml.core.base_component.BaseComponent`](zenml.core.md#zenml.core.base_component.BaseComponent)

Base class for all ZenML Artifact Store.

Every ZenML Artifact Store should override this class. _class_ Config[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.Config)

Bases: `object`

Configuration of settings. env\_prefix _= 'zenml\_artifact\_store\_'_[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.Config.env_prefix) _static_ get\_component\_name\_from\_uri\(_artifact\_uri: str_\) → str[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.get_component_name_from_uri)

Gets component name from artifact URI.Parameters

**artifact\_uri** – URI to artifact.Returns

Name of the component \(str\). get\_serialization\_dir\(\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.get_serialization_dir)

Gets the local path where artifacts are stored. path_: str_[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.path) resolve\_uri\_locally\(_artifact\_uri: str_, _path: Optional\[str\] = None_\) → str[¶](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore.resolve_uri_locally)

Takes a URI that points within the artifact store, downloads the URI locally, then returns local URI.Parameters

* **artifact\_uri** – uri to artifact.
* **path** – optional path to download to. If None, is inferred.

Returns

Locally resolved uri \(str\).

### zenml.artifact\_stores.gcp\_artifact\_store module[¶](zenml.artifact_stores.md#module-zenml.artifact_stores.gcp_artifact_store)

 _class_ zenml.artifact\_stores.gcp\_artifact\_store.GCPArtifactStore\(_\*_, _uuid: uuid.UUID = None_, _path: str_\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.gcp_artifact_store.GCPArtifactStore)

Bases: [`zenml.artifact_stores.base_artifact_store.BaseArtifactStore`](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)

Artifact Store for Google Cloud Storage based artifacts. _classmethod_ must\_be\_gcs\_path\(_v: str_\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.gcp_artifact_store.GCPArtifactStore.must_be_gcs_path)

Validates that the path is a valid gcs path. path_: str_[¶](zenml.artifact_stores.md#zenml.artifact_stores.gcp_artifact_store.GCPArtifactStore.path) uuid_: Optional\[UUID\]_[¶](zenml.artifact_stores.md#zenml.artifact_stores.gcp_artifact_store.GCPArtifactStore.uuid)

### zenml.artifact\_stores.local\_artifact\_store module[¶](zenml.artifact_stores.md#module-zenml.artifact_stores.local_artifact_store)

 _class_ zenml.artifact\_stores.local\_artifact\_store.LocalArtifactStore\(_\*_, _uuid: uuid.UUID = None_, _path: str_\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.local_artifact_store.LocalArtifactStore)

Bases: [`zenml.artifact_stores.base_artifact_store.BaseArtifactStore`](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)

Artifact Store for local artifacts. _classmethod_ must\_be\_local\_path\(_v: str_\)[¶](zenml.artifact_stores.md#zenml.artifact_stores.local_artifact_store.LocalArtifactStore.must_be_local_path)

Validates that the path is a valid gcs path. path_: str_[¶](zenml.artifact_stores.md#zenml.artifact_stores.local_artifact_store.LocalArtifactStore.path) uuid_: Optional\[UUID\]_[¶](zenml.artifact_stores.md#zenml.artifact_stores.local_artifact_store.LocalArtifactStore.uuid)

### Module contents[¶](zenml.artifact_stores.md#module-zenml.artifact_stores)

 [Back to top](zenml.artifact_stores.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


