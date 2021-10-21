Module zenml.core.mapping_utils
===============================

Functions
---------

    
`get_component_from_key(key: str, mapping: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]) ‑> zenml.core.base_component.BaseComponent`
:   Given a key and a mapping, return an initialized component.
    
    Args:
        key: Unique key.
        mapping: Dict of type str -> UUIDSourceTuple.
    
    Returns:
        An object which is a subclass of type BaseComponent.

    
`get_components_from_store(store_name: str, mapping: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]) ‑> Dict[str, zenml.core.base_component.BaseComponent]`
:   Returns a list of components from a store.
    
    Args:
        store_name: Name of the store.
        mapping: Dict of type str -> UUIDSourceTuple.
    
    Returns:
        A dict of objects which are a subclass of type BaseComponent.

    
`get_key_from_uuid(uuid: uuid.UUID, mapping: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]) ‑> str`
:   Return they key that points to a certain uuid in a mapping.
    
    Args:
        uuid: uuid to query.
        mapping: Dict mapping keys to UUIDs and source information.
    
    Returns:
        Returns the key from the mapping.

Classes
-------

`UUIDSourceTuple(**data: Any)`
:   Container used to store UUID and source information
    of a single BaseComponent subclass.
    
    Attributes:
        uuid: Identifier of the BaseComponent
        source: Contains the fully qualified class name and information
         about a git hash/tag. E.g. foo.bar.BaseComponentSubclass@git_tag
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `source: str`
    :

    `uuid: uuid.UUID`
    :