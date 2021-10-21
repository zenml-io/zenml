Module zenml.utils.yaml_utils
=============================

Functions
---------

    
`is_yaml(file_path: str) ‑> bool`
:   Returns True if file_path is YAML, else False
    
    Args:
        file_path: Path to YAML file.
    
    Returns:
        True if is yaml, else False.

    
`read_json(file_path: str) ‑> Any`
:   Read JSON on file path and returns contents as dict.
    
    Args:
        file_path: Path to JSON file.

    
`read_yaml(file_path: str) ‑> Dict`
:   Read YAML on file path and returns contents as dict.
    
    Args:
        file_path(str): Path to YAML file.
    
    Returns:
        Contents of the file in a dict.
    
    Raises:
        FileNotFoundError if file does not exist.

    
`write_json(file_path: str, contents: Dict)`
:   Write contents as JSON format to file_path.
    
    Args:
        file_path: Path to JSON file.
        contents: Contents of JSON file as dict.
    
    Returns:
        Contents of the file in a dict.
    
    Raises:
        FileNotFoundError if directory does not exist.

    
`write_yaml(file_path: str, contents: Dict)`
:   Write contents as YAML format to file_path.
    
    Args:
        file_path: Path to YAML file.
        contents: Contents of YAML file as dict.
    
    Raises:
        FileNotFoundError if directory does not exist.