# zenml.integrations.langchain package

## Subpackages

* [zenml.integrations.langchain.materializers package](zenml.integrations.langchain.materializers.md)
  * [Submodules](zenml.integrations.langchain.materializers.md#submodules)
  * [zenml.integrations.langchain.materializers.document_materializer module](zenml.integrations.langchain.materializers.md#zenml-integrations-langchain-materializers-document-materializer-module)
  * [zenml.integrations.langchain.materializers.openai_embedding_materializer module](zenml.integrations.langchain.materializers.md#zenml-integrations-langchain-materializers-openai-embedding-materializer-module)
  * [zenml.integrations.langchain.materializers.vector_store_materializer module](zenml.integrations.langchain.materializers.md#zenml-integrations-langchain-materializers-vector-store-materializer-module)
  * [Module contents](zenml.integrations.langchain.materializers.md#module-contents)

## Module contents

Initialization of the langchain integration.

### *class* zenml.integrations.langchain.LangchainIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of langchain integration for ZenML.

#### NAME *= 'langchain'*

#### REQUIREMENTS *: List[str]* *= ['langchain==0.0.325', 'pyyaml>=6.0.1', 'tenacity!=8.4.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pyyaml', 'tenacity']*

#### *classmethod* activate() → None

Activates the integration.
