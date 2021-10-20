Module zenml.materializers.pandas_materializer
==============================================

Classes
-------

`PandasMaterializer(artifact: BaseArtifact)`
:   Materializer to read data to and from pandas.
    
    Initializes a materializer with the given artifact.

    ### Ancestors (in MRO)

    * zenml.materializers.base_materializer.BaseMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> pandas.core.frame.DataFrame`
    :   Reads pd.Dataframe from a parquet file.

    `handle_return(self, df: pandas.core.frame.DataFrame)`
    :   Writes a pandas dataframe to the specified filename.
        
        Args:
            df: The pandas dataframe to write.