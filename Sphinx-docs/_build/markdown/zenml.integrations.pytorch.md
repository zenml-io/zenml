# zenml.integrations.pytorch package

## Subpackages

* [zenml.integrations.pytorch.materializers package](zenml.integrations.pytorch.materializers.md)
  * [Submodules](zenml.integrations.pytorch.materializers.md#submodules)
  * [zenml.integrations.pytorch.materializers.base_pytorch_materializer module](zenml.integrations.pytorch.materializers.md#zenml-integrations-pytorch-materializers-base-pytorch-materializer-module)
  * [zenml.integrations.pytorch.materializers.pytorch_dataloader_materializer module](zenml.integrations.pytorch.materializers.md#zenml-integrations-pytorch-materializers-pytorch-dataloader-materializer-module)
  * [zenml.integrations.pytorch.materializers.pytorch_module_materializer module](zenml.integrations.pytorch.materializers.md#zenml-integrations-pytorch-materializers-pytorch-module-materializer-module)
  * [Module contents](zenml.integrations.pytorch.materializers.md#module-contents)

## Submodules

## zenml.integrations.pytorch.utils module

## Module contents

Initialization of the PyTorch integration.

### *class* zenml.integrations.pytorch.PytorchIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of PyTorch integration for ZenML.

#### NAME *= 'pytorch'*

#### REQUIREMENTS *: List[str]* *= ['torch']*

#### *classmethod* activate() → None

Activates the integration.
