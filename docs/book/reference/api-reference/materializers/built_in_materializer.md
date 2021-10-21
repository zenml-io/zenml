Module zenml.materializers.built_in_materializer
================================================

Classes
-------

`BuiltInMaterializer(artifact: BaseArtifact)`
:   Read/Write JSON files.
    
    Initializes a materializer with the given artifact.

    ### Ancestors (in MRO)

    * zenml.materializers.base_materializer.BaseMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> Any`
    :   Reads basic primitive types from json.

    `handle_return(self, data: Any)`
    :   Handles basic built-in types and stores them as json