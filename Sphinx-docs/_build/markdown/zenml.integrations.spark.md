# zenml.integrations.spark package

## Subpackages

* [zenml.integrations.spark.flavors package](zenml.integrations.spark.flavors.md)
  * [Submodules](zenml.integrations.spark.flavors.md#submodules)
  * [zenml.integrations.spark.flavors.spark_on_kubernetes_step_operator_flavor module](zenml.integrations.spark.flavors.md#zenml-integrations-spark-flavors-spark-on-kubernetes-step-operator-flavor-module)
  * [zenml.integrations.spark.flavors.spark_step_operator_flavor module](zenml.integrations.spark.flavors.md#zenml-integrations-spark-flavors-spark-step-operator-flavor-module)
  * [Module contents](zenml.integrations.spark.flavors.md#module-contents)
* [zenml.integrations.spark.materializers package](zenml.integrations.spark.materializers.md)
  * [Submodules](zenml.integrations.spark.materializers.md#submodules)
  * [zenml.integrations.spark.materializers.spark_dataframe_materializer module](zenml.integrations.spark.materializers.md#zenml-integrations-spark-materializers-spark-dataframe-materializer-module)
  * [zenml.integrations.spark.materializers.spark_model_materializer module](zenml.integrations.spark.materializers.md#zenml-integrations-spark-materializers-spark-model-materializer-module)
  * [Module contents](zenml.integrations.spark.materializers.md#module-contents)
* [zenml.integrations.spark.step_operators package](zenml.integrations.spark.step_operators.md)
  * [Submodules](zenml.integrations.spark.step_operators.md#submodules)
  * [zenml.integrations.spark.step_operators.kubernetes_step_operator module](zenml.integrations.spark.step_operators.md#zenml-integrations-spark-step-operators-kubernetes-step-operator-module)
  * [zenml.integrations.spark.step_operators.spark_entrypoint_configuration module](zenml.integrations.spark.step_operators.md#zenml-integrations-spark-step-operators-spark-entrypoint-configuration-module)
  * [zenml.integrations.spark.step_operators.spark_step_operator module](zenml.integrations.spark.step_operators.md#zenml-integrations-spark-step-operators-spark-step-operator-module)
  * [Module contents](zenml.integrations.spark.step_operators.md#module-contents)

## Module contents

The Spark integration module to enable distributed processing for steps.

### *class* zenml.integrations.spark.SparkIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Spark integration for ZenML.

#### NAME *= 'spark'*

#### REQUIREMENTS *: List[str]* *= ['pyspark==3.2.1']*

#### *classmethod* activate() → None

Activating the corresponding Spark materializers.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Spark integration.

Returns:
: The flavor wrapper for the step operator flavor
