Module zenml.utils.source_utils
===============================
These utils are predicated on the following definitions:

* class_source: This is a python-import type path to a class, e.g.
some.mod.class
* module_source: This is a python-import type path to a module, e.g. some.mod
* file_path, relative_path, absolute_path: These are file system paths.
* source: This is a class_source or module_source. If it is a class_source, it
can also be optionally pinned.
* pin: Whatever comes after the `@` symbol from a source, usually the git sha
or the version of zenml as a string.

Functions
---------

    
`create_zenml_pin() ‑> str`
:   Creates a ZenML pin for source pinning from release version.

    
`get_absolute_path_from_module_source(module: str) ‑> str`
:   Get a directory path from module source.
    
    E.g. `zenml.core.step` will return `full/path/to/zenml/core/step`.
    
    Args:
        module: A module e.g. `zenml.core.step`.

    
`get_class_source_from_source(source: str) ‑> Optional[str]`
:   Gets class source from source, i.e. module.path@version, returns version.
    
    Args:
        source: source pointing to potentially pinned sha.

    
`get_module_source_from_class(class_: Union[Type, str]) ‑> Optional[str]`
:   Takes class input and returns module_source. If class is already string
    then returns the same.
    
    Args:
        class_: object of type class.

    
`get_module_source_from_file_path(file_path: str) ‑> str`
:   Gets module_source from a file_path. E.g. `/home/myrepo/step/trainer.py`
    returns `myrepo.step.trainer` if `myrepo` is the root of the repo.
    
    Args:
        file_path: Absolute file path to a file within the module.

    
`get_module_source_from_source(source: str) ‑> str`
:   Gets module source from source. E.g. `some.module.file.class@version`,
    returns `some.module`.
    
    Args:
        source: source pointing to potentially pinned sha.

    
`get_path_from_source(source: str) ‑> str`
:   Get file path from source
    
    Args:
        source: class_source e.g. this.module.Class.

    
`get_pin_from_source(source: str) ‑> Optional[str]`
:   Gets pin from source, i.e. module.path@pin, returns pin.
    
    Args:
        source: class_source e.g. this.module.Class[@pin].

    
`get_relative_path_from_module_source(module_source: str) ‑> str`
:   Get a directory path from module, relative to root of repository.
    
    E.g. zenml.core.step will return zenml/core/step.
    
    Args:
        module_source: A module e.g. zenml.core.step

    
`is_standard_pin(pin: str) ‑> bool`
:   Returns True if pin is valid ZenML pin, else False.
    
    Args:
        pin: potential ZenML pin like 'zenml_0.1.1'

    
`is_standard_source(source: str) ‑> bool`
:   Returns True if source is a standard ZenML source.
    
    Args:
        source (str): class_source e.g. this.module.Class[@pin].

    
`load_source_path_class(source: str) ‑> Type`
:   Loads a Python class from the source.
    
    Args:
        source: class_source e.g. this.module.Class[@sha]

    
`resolve_class(class_: Type) ‑> str`
:   Resolves a a class into a serializable source string.
    
    Args:
        class_: A Python Class reference.
    
    Returns: source_path e.g. this.module.Class.

    
`resolve_standard_source(source: str) ‑> str`
:   Creates a ZenML pin for source pinning from release version.
    
    Args:
        source: class_source e.g. this.module.Class.