# zenml.integrations.s3 package

## Subpackages

* [zenml.integrations.s3.artifact_stores package](zenml.integrations.s3.artifact_stores.md)
  * [Submodules](zenml.integrations.s3.artifact_stores.md#submodules)
  * [zenml.integrations.s3.artifact_stores.s3_artifact_store module](zenml.integrations.s3.artifact_stores.md#zenml-integrations-s3-artifact-stores-s3-artifact-store-module)
  * [Module contents](zenml.integrations.s3.artifact_stores.md#module-contents)
* [zenml.integrations.s3.flavors package](zenml.integrations.s3.flavors.md)
  * [Submodules](zenml.integrations.s3.flavors.md#submodules)
  * [zenml.integrations.s3.flavors.s3_artifact_store_flavor module](zenml.integrations.s3.flavors.md#zenml-integrations-s3-flavors-s3-artifact-store-flavor-module)
  * [Module contents](zenml.integrations.s3.flavors.md#module-contents)

## Module contents

Initialization of the S3 integration.

The S3 integration allows the use of cloud artifact stores and file
operations on S3 buckets.

### *class* zenml.integrations.s3.S3Integration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of S3 integration for ZenML.

#### NAME *= 's3'*

#### REQUIREMENTS *: List[str]* *= ['s3fs>2022.3.0', 'boto3', 'aws-profile-manager']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the s3 integration.

Returns:
: List of stack component flavors for this integration.
