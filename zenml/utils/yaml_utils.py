#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
from typing import Text, Dict

import yaml

from zenml.utils import path_utils


def write_yaml(file_path: Text, contents: Dict):
    """
    Write contents as YAML format to file_path.

    Args:
        file_path (str): Path to YAML file.
        contents (dict): Contents of YAML file as dict.
    """
    if not path_utils.is_remote(file_path):
        dir_ = str(Path(file_path).parent)
        if not path_utils.is_dir(dir_):
            # If it is a local path and it doesnt exist, raise Exception.
            raise Exception(f'Directory {dir_} does not exist.')
    path_utils.write_file_contents(file_path, yaml.dump(contents))


def read_yaml(file_path: Text):
    """
    Read YAML on file path and returns contents as dict.

    Args:
        file_path (str): Path to YAML file.
    """
    if path_utils.file_exists(file_path):
        with open(file_path, 'r') as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)
    else:
        raise Exception(f'{file_path} does not exist.')


def is_yaml(file_path: Text):
    """
    Returns True if file_path is YAML, else False

    Args:
        file_path (str): Path to YAML file.
    """
    if file_path.endswith('yaml') or file_path.endswith('yml'):
        return True
    return False


def write_json(file_path: Text, contents: Dict):
    """
    Write contents as JSON format to file_path.

    Args:
        file_path (str): Path to JSON file.
        contents (dict): Contents of JSON file as dict.
    """
    if not path_utils.is_remote(file_path):
        dir_ = str(Path(file_path).parent)
        if not path_utils.is_dir(dir_):
            # If it is a local path and it doesnt exist, raise Exception.
            raise Exception(f'Directory {dir_} does not exist.')
    path_utils.write_file_contents(file_path, json.dumps(contents))


def read_json(file_path: Text):
    """
    Read JSON on file path and returns contents as dict.

    Args:
        file_path (str): Path to JSON file.
    """
    if path_utils.file_exists(file_path):
        with open(file_path, 'r') as f:
            return json.loads(f.read())
    else:
        raise Exception(f'{file_path} does not exist.')
