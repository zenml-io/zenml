Module zenml.materializers.keras_meterializer
=============================================

Classes
-------

`KerasMaterializer(artifact: BaseArtifact)`
:   Materializer to read/write Keras models.
    
    Initializes a materializer with the given artifact.

    ### Ancestors (in MRO)

    * zenml.materializers.base_materializer.BaseMaterializer

    ### Class variables

    `ASSOCIATED_TYPES`
    :

    ### Methods

    `handle_input(self, data_type: Type) ‑> keras.engine.training.Model`
    :   Reads and returns a Keras model.
        
        Returns:
            A tf.keras.Model model.

    `handle_return(self, model: keras.engine.training.Model)`
    :   Writes a keras model.
        
        Args:
            model: A tf.keras.Model model.