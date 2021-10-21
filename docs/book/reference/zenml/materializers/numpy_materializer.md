Module zenml.materializers.numpy_materializer
=============================================

Classes
-------

`NumpyMaterializer(artifact: BaseArtifact)`
:   Materializer to read data to and from pandas.
    
    Initializes a materializer with the given artifact.

    ### Ancestors (in MRO)

    * zenml.materializers.base_materializer.BaseMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> numpy.ndarray`
    :   Reads numpy array from parquet file.

    `handle_return(self, arr: numpy.ndarray)`
    :   Writes a np.ndarray to the artifact store as a parquet file.
        
        Args:
            arr: The numpy array to write.