Module zenml.steps.base_step
============================

Functions
---------

    
`check_dict_keys_match(x: Dict, y: Dict) ‑> bool`
:   Checks whether there is even one key shared between two dicts.
    
    Returns:
        True if there is a shared key, otherwise False.

Classes
-------

`BaseStep(*args, **kwargs)`
:   The base implementation of a ZenML Step which will be inherited by all
    the other step implementations

    ### Class variables

    `CONFIG`
    :

    `INPUT_SIGNATURE`
    :

    `OUTPUT_SIGNATURE`
    :

    ### Instance variables

    `component`
    :   Returns a TFX component.

    ### Methods

    `process(self, *args, **kwargs)`
    :   Abstract method for core step logic.

    `resolve_signature_materializers(self, signature: Dict[str, Type], is_input: bool = True) ‑> None`
    :   Takes either the INPUT_SIGNATURE and OUTPUT_SIGNATURE and resolves
        the materializers for them in the `spec_materializer_registry`.
        
        Args:
            signature: Either self.INPUT_SIGNATURE or self.OUTPUT_SIGNATURE.
            is_input: If True, then self.INPUT_SPEC used, else self.OUTPUT_SPEC.

    `with_return_materializers(self, materializers: Union[Type[zenml.materializers.base_materializer.BaseMaterializer], Dict[str, Type[zenml.materializers.base_materializer.BaseMaterializer]]])`
    :   Inject materializers from the outside. If one materializer is passed
        in then all outputs are assigned that materializer. If a dict is passed
        in then we make sure the output names match.
        
        Args:
            materializers: Either a `Type[BaseMaterializer]`, or a
            dict that maps {output_name: Type[BaseMaterializer]}.

`BaseStepMeta(*args, **kwargs)`
:   Meta class for `BaseStep`.
    
    Checks whether everything passed in:
    * Has a matching materializer.
    * Is a subclass of the Config class

    ### Ancestors (in MRO)

    * builtins.type