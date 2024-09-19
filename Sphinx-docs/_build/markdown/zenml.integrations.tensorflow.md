# zenml.integrations.tensorflow package

## Subpackages

* [zenml.integrations.tensorflow.materializers package](zenml.integrations.tensorflow.materializers.md)
  * [Submodules](zenml.integrations.tensorflow.materializers.md#submodules)
  * [zenml.integrations.tensorflow.materializers.keras_materializer module](zenml.integrations.tensorflow.materializers.md#zenml-integrations-tensorflow-materializers-keras-materializer-module)
  * [zenml.integrations.tensorflow.materializers.tf_dataset_materializer module](zenml.integrations.tensorflow.materializers.md#zenml-integrations-tensorflow-materializers-tf-dataset-materializer-module)
  * [Module contents](zenml.integrations.tensorflow.materializers.md#module-contents)

## Module contents

Initialization for TensorFlow integration.

### *class* zenml.integrations.tensorflow.TensorflowIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Tensorflow integration for ZenML.

#### NAME *= 'tensorflow'*

#### REQUIREMENTS *: List[str]* *= []*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['typing-extensions']*

#### *classmethod* activate() → None

Activates the integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Defines platform specific requirements for the integration.

Args:
: target_os: The target operating system.

Returns:
: A list of requirements.
