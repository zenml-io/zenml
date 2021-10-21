Module zenml.core.component_factory
===================================
Factory to register all components.

Classes
-------

`ComponentFactory(name: str)`
:   Definition of ComponentFactory to track all BaseComponent subclasses.
    
    All BaseComponents (including custom ones) are to be
    registered here.
    
    Constructor for the factory.
    
    Args:
        name: Unique name for the factory.

    ### Methods

    `get_components(self) ‑> Dict[str, Type[zenml.core.base_component.BaseComponent]]`
    :   Return all components

    `get_single_component(self, key: str) ‑> Type[zenml.core.base_component.BaseComponent]`
    :   Get a registered component from a key.

    `register(self, name: str) ‑> Callable`
    :   Class decorator to register component classes to the internal registry.
        
        Args:
            name: The name of the component.
        
        Returns:
            A class decorator which registers the class at this ComponentFactory instance.

    `register_component(self, key: str, component: Type[zenml.core.base_component.BaseComponent])`
    :   Registers a single component class for a given key.