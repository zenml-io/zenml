Module zenml.core.git_wrapper
=============================
Wrapper class to handle Git integration

Classes
-------

`GitWrapper(repo_path: str)`
:   Wrapper class for Git.
    
    This class is responsible for handling git interactions, primarily
    handling versioning of different steps in pipelines.
    
    Initialize GitWrapper. Should be initialize by ZenML Repository.
    Args:
        repo_path:
    
    Raises:
        InvalidGitRepositoryError: If repository is not a git repository.
        NoSuchPathError: If the repo_path does not exist.

    ### Methods

    `add_gitignore(self, items: List[str])`
    :   Adds `items` to .gitignore, if .gitignore exists. Otherwise creates
        and adds.
        
        Args:
            items (list[str]): Items to add.

    `check_file_committed(self, file_path: str) ‑> bool`
    :   Checks file is committed. If yes, return True, else False.
        
        Args:
            file_path (str): Path to any file within the ZenML repo.

    `check_module_clean(self, source: str)`
    :   Returns True if all files within source's module are committed.
        
        Args:
            source (str): relative module path pointing to a Class.

    `checkout(self, sha_or_branch: str = None, directory: str = None)`
    :   Wrapper for git checkout
        
        Args:
            sha_or_branch: hex string of len 40 representing git sha OR
            name of branch
            directory (str): relative path to directory to scope checkout

    `get_current_sha(self) ‑> str`
    :   Finds the git sha that each file within the module is currently on.

    `is_valid_source(self, source: str) ‑> bool`
    :   Checks whether the source_path is valid or not.
        
        Args:
            source (str): class_source e.g. this.module.Class[@pin].

    `load_source_path_class(self, source: str) ‑> Type`
    :   Loads a Python class from the source.
        
        Args:
            source: class_source e.g. this.module.Class[@sha]

    `reset(self, directory: str = None)`
    :   Wrapper for `git reset HEAD <directory>`.
        
        Args:
            directory (str): relative path to directory to scope checkout

    `resolve_class(self, class_: Type) ‑> str`
    :   Resolves
        Args:
            class_: A Python Class reference.
        
        Returns: source_path e.g. this.module.Class[@pin].

    `resolve_class_source(self, class_source: str) ‑> str`
    :   Resolves class_source with an optional pin.
        Takes source (e.g. this.module.ClassName), and appends relevant
        sha to it if the files within `module` are all committed. If even one
        file is not committed, then returns `source` unchanged.
        
        Args:
            class_source (str): class_source e.g. this.module.Class

    `stash(self)`
    :   Wrapper for git stash

    `stash_pop(self)`
    :   Wrapper for git stash pop. Only pops if there's something to pop.