Module zenml.materializers.spec_materializer_registry
=====================================================

Classes
-------

`SpecMaterializerRegistry()`
:   Matches spec of a step to a materializer.
    
    Materializer types registry.

    ### Methods

    `get_materializer_types(self) ‑> Dict[str, Type[_ForwardRef('BaseMaterializer')]]`
    :   Get all registered materializers.

    `get_single_materializer_type(self, key: str) ‑> Type[_ForwardRef('BaseMaterializer')]`
    :   Gets a single pre-registered materializer type based on `key`.

    `is_registered(self, key: Type[Any]) ‑> bool`
    :   Returns true if key type is registered, else returns False.

    `register_materializer_type(self, key: str, type_: Type[_ForwardRef('BaseMaterializer')])`
    :   Registers a new materializer.
        
        Args:
            key: Name of input or output parameter.
            type_: A BaseMaterializer subclass.