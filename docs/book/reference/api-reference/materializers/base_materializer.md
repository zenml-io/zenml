Module zenml.materializers.base_materializer
============================================

Classes
-------

`BaseMaterializer(artifact: BaseArtifact)`
:   Base Materializer to realize artifact data.
    
    Initializes a materializer with the given artifact.

    ### Descendants

    * zenml.materializers.beam_materializer.BeamMaterializer
    * zenml.materializers.built_in_materializer.BuiltInMaterializer
    * zenml.materializers.keras_meterializer.KerasMaterializer
    * zenml.materializers.numpy_materializer.NumpyMaterializer
    * zenml.materializers.pandas_materializer.PandasMaterializer
    * zenml.materializers.tf_dataset_materializer.TensorflowDatasetMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> Any`
    :   Write logic here to handle input of the step function.
        
        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.

    `handle_return(self, data: Any) ‑> None`
    :   Write logic here to handle return of the step function.
        
        Args:
            Any object that is specified as an input artifact of the step.

`BaseMaterializerMeta(*args, **kwargs)`
:   Metaclass responsible for registering different BaseMaterializer
    subclasses for reading/writing artifacts.

    ### Ancestors (in MRO)

    * builtins.type