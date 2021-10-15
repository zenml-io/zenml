#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from zenml.utils import path_utils


def write_yaml(file_path: str, contents: Dict):
    """Write contents as YAML format to file_path.

    Args:
        file_path: Path to YAML file.
        contents: Contents of YAML file as dict.

    Raises:
        FileNotFoundError if directory does not exist.
    """
    if not path_utils.is_remote(file_path):
        dir_ = str(Path(file_path).parent)
        if not path_utils.is_dir(dir_):
            raise FileNotFoundError(f"Directory {dir_} does not exist.")
    path_utils.write_file_contents_as_string(file_path, yaml.dump(contents))


def read_yaml(file_path: str) -> Dict:
    """Read YAML on file path and returns contents as dict.

    Args:
        file_path(str): Path to YAML file.

    Returns:
        Contents of the file in a dict.

    Raises:
        FileNotFoundError if file does not exist.
    """
    if path_utils.file_exists(file_path):
        contents = path_utils.read_file_contents_as_string(file_path)
        return yaml.load(contents, Loader=yaml.FullLoader)
    else:
        raise FileNotFoundError(f"{file_path} does not exist.")


def is_yaml(file_path: str) -> bool:
    """Returns True if file_path is YAML, else False

    Args:
        file_path: Path to YAML file.

    Returns:
        True if is yaml, else False.
    """
    if file_path.endswith("yaml") or file_path.endswith("yml"):
        return True
    return False


def write_json(file_path: str, contents: Dict):
    """Write contents as JSON format to file_path.

    Args:
        file_path: Path to JSON file.
        contents: Contents of JSON file as dict.

    Returns:
        Contents of the file in a dict.

    Raises:
        FileNotFoundError if directory does not exist.
    """
    if not path_utils.is_remote(file_path):
        dir_ = str(Path(file_path).parent)
        if not path_utils.is_dir(dir_):
            # If it is a local path and it doesnt exist, raise Exception.
            raise FileNotFoundError(f"Directory {dir_} does not exist.")
    path_utils.write_file_contents_as_string(file_path, json.dumps(contents))


def read_json(file_path: str) -> Any:
    """Read JSON on file path and returns contents as dict.

    Args:
        file_path: Path to JSON file.
    """
    if path_utils.file_exists(file_path):
        contents = path_utils.read_file_contents_as_string(file_path)
        return json.loads(contents)
    else:
        raise FileNotFoundError(f"{file_path} does not exist.")
