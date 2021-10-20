Module zenml.materializers.tf_dataset_materializer
==================================================

Classes
-------

`TensorflowDatasetMaterializer(artifact: BaseArtifact)`
:   Materializer to read data to and from beam.
    
    Initializes a materializer with the given artifact.

    ### Ancestors (in MRO)

    * zenml.materializers.base_materializer.BaseMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> Any`
    :   Reads data into tf.data.Dataset

    `handle_return(self, dataset: tensorflow.python.data.ops.dataset_ops.DatasetV2)`
    :   Persists a tf.data.Dataset object.