Module zenml.materializers.default_materializer_registry
========================================================

Classes
-------

`DefaultMaterializerRegistry()`
:   Matches a python type to a default materializer.

    ### Class variables

    `materializer_types: ClassVar[Dict[Type[Any], Type[_ForwardRef('BaseMaterializer')]]]`
    :

    ### Static methods

    `register_materializer_type(key: Type[Any], type_: Type[_ForwardRef('BaseMaterializer')])`
    :   Registers a new materializer.
        
        Args:
            key: Indicates the type of an object.
            type_: A BaseMaterializer subclass.

    ### Methods

    `get_materializer_types(self) ‑> Dict[Type[Any], Type[_ForwardRef('BaseMaterializer')]]`
    :   Get all registered materializers.

    `get_single_materializer_type(self, key: Type[Any]) ‑> BaseMaterializer`
    :   Get a single materializers based on the key.
        
        Args:
            key: Indicates the type of an object.
        
        Returns:
            Instance of a `BaseMaterializer` subclass initialized with the
            artifact of this factory.

    `is_registered(self, key: Type[Any]) ‑> bool`
    :   Returns true if key type is registered, else returns False.

    `register_and_overwrite_type(self, key: Type[Any], type_: Type[_ForwardRef('BaseMaterializer')])`
    :   Registers a new materializer and also overwrites a default if set.
        
        Args:
            key: Indicates the type of an object.
            type_: A BaseMaterializer subclass.