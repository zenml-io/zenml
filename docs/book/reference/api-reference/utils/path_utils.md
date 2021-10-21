Module zenml.utils.path_utils
=============================
File utilities

Functions
---------

    
`append_file(file_path: str, file_contents: str)`
:   Appends file_contents to file.
    
    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.

    
`copy(source: str, destination: str, overwrite: bool = False)`
:   Copies dir from source to destination.
    
    Args:
        source(str): Path to copy from.
        destination(str): Path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.

    
`copy_dir(source_dir: str, destination_dir: str, overwrite: bool = False)`
:   Copies dir from source to destination.
    
    Args:
        source_dir: Path to copy from.
        destination_dir: Path to copy to.
        overwrite: Boolean, if false, then throws an error before overwrite.

    
`create_dir_if_not_exists(dir_path: str)`
:   Creates directory if it does not exist.
    
    Args:
        dir_path(str): Local path in filesystem.

    
`create_dir_recursive_if_not_exists(dir_path: str)`
:   Creates directory recursively if it does not exist.
    
    Args:
        dir_path: Local path in filesystem.

    
`create_file_if_not_exists(file_path: str, file_contents: str = '{}')`
:   Creates directory if it does not exist.
    
    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.

    
`create_tarfile(source_dir: str, output_filename: str = 'zipped.tar.gz', exclude_function: Callable = None)`
:   Create a compressed representation of source_dir.
    
    Args:
        source_dir: Path to source dir.
        output_filename: Name of outputted gz.
        exclude_function: Function that determines whether to exclude file.

    
`extract_tarfile(source_tar: str, output_dir: str)`
:   Untars a compressed tar file to output_dir.
    
    Args:
        source_tar: Path to a tar compressed file.
        output_dir: Directory where to uncompress.

    
`file_exists(path: str) ‑> bool`
:   Returns true if file exists at path.
    
    Args:
        path: Local path in filesystem.
    
    Returns:
        True if file exists, else False.

    
`find_files(dir_path, pattern) ‑> List[str]`
:   Find files in a directory that match pattern.
    
    Args:
        dir_path: Path to directory.
        pattern: pattern like *.png.
    
    Yields:
         All matching filenames if found, else None.

    
`get_grandparent(dir_path: str) ‑> str`
:   Get grandparent of dir.
    
    Args:
        dir_path: Path to directory.
    
    Returns:
        The input paths parents parent.

    
`get_parent(dir_path: str) ‑> str`
:   Get parent of dir.
    
    Args:
        dir_path(str): Path to directory.
    
    Returns:
        Parent (stem) of the dir as a string.

    
`get_zenml_config_dir(path: str = '/home/hamza/workspace/maiot/github_temp/zenml') ‑> str`
:   Recursive function to find the zenml config starting from path.
    
    Args:
        path (Default value = os.getcwd()): Path to check.
    
    Returns:
        The full path with the resolved zenml directory.
    
    Raises:
        InitializationException if directory not found until root of OS.

    
`get_zenml_dir(path: str = '/home/hamza/workspace/maiot/github_temp/zenml') ‑> str`
:   Recursive function to find the zenml config starting from path.
    
    Args:
        path (Default value = os.getcwd()): Path to check.
    
    Returns:
        The full path with the resolved zenml directory.
    
    Raises:
        InitializationException if directory not found until root of OS.

    
`is_dir(dir_path: str) ‑> bool`
:   Returns true if dir_path points to a dir.
    
    Args:
        dir_path: Local path in filesystem.
    
    Returns:
        True if is dir, else False.

    
`is_gcs_path(path: str) ‑> bool`
:   Returns True if path is on Google Cloud Storage.
    
    Args:
        path: Any path as a string.
    
    Returns:
        True if gcs path, else False.

    
`is_remote(path: str) ‑> bool`
:   Returns True if path exists remotely.
    
    Args:
        path: Any path as a string.
    
    Returns:
        True if remote path, else False.

    
`is_root(path: str) ‑> bool`
:   Returns true if path has no parent in local filesystem.
    
    Args:
        path: Local path in filesystem.
    
    Returns:
        True if root, else False.

    
`is_zenml_dir(path: str) ‑> bool`
:   Check if dir is a zenml dir or not.
    
    Args:
        path: Path to the root.
    
    Returns:
        True if path contains a zenml dir, False if not.

    
`list_dir(dir_path: str, only_file_names: bool = False) ‑> List[str]`
:   Returns a list of files under dir.
    
    Args:
        dir_path: Path in filesystem.
        only_file_names: Returns only file names if True.
    
    Returns:
        List of full qualified paths.

    
`load_csv_header(csv_path: str) ‑> List[str]`
:   Gets header column of csv and returns list.
    
    Args:
        csv_path: Path to csv file.

    
`move(source: str, destination: str, overwrite: bool = False)`
:   Moves dir from source to destination. Can be used to rename.
    
    Args:
        source: Local path to copy from.
        destination: Local path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.

    
`read_file_contents_as_string(file_path: str)`
:   Reads contents of file.
    
    Args:
        file_path: Path to file.

    
`resolve_relative_path(path: str) ‑> str`
:   Takes relative path and resolves it absolutely.
    
    Args:
      path: Local path in filesystem.
    
    Returns:
        Resolved path.

    
`rm_dir(dir_path: str)`
:   Deletes dir recursively. Dangerous operation.
    
    Args:
        dir_path: Dir to delete.

    
`rm_file(file_path: str)`
:   Deletes file. Dangerous operation.
    
    Args:
        file_path: Path of file to delete.

    
`walk(dir_path) ‑> Iterable[Tuple[Union[bytes, str], List[Union[bytes, str]], List[Union[bytes, str]]]]`
:   Walks down the dir_path.
    
    Args:
        dir_path: Path of dir to walk down.
    
    Returns:
        Iterable of tuples to walk down.

    
`write_file_contents_as_string(file_path: str, content: str)`
:   Writes contents of file.
    
    Args:
        file_path: Path to file.
        content: Contents of file.