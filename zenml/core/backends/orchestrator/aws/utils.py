import base64
import json
import os
from typing import Dict, Text

import boto3

from zenml.utils.constants import ZENML_BASE_IMAGE_NAME, AWS_ENTRYPOINT

AWS_ACCESS_KEY_ID = 'AWS_ACCESS_KEY_ID'
AWS_SECRET_ACCESS_KEY = 'AWS_SECRET_ACCESS_KEY'
AWS_REGION = 'AWS_REGION'


def _get_container_params(config):
    config_encoded = base64.b64encode(json.dumps(config).encode())
    return f'python -m {AWS_ENTRYPOINT} run_pipeline --config_b64 ' \
           f'{config_encoded.decode()}'


def get_startup_script(config: Dict,
                       zenml_image: Text = ZENML_BASE_IMAGE_NAME):
    c_params = _get_container_params(config)
    return f"#!/bin/bash\n" \
           f"sudo HOME=/home/root docker run --net=host {zenml_image} {c_params}"


def setup_session():
    session = boto3.Session()
    credentials = session.get_credentials()
    os.environ[AWS_ACCESS_KEY_ID] = credentials.access_key
    os.environ[AWS_SECRET_ACCESS_KEY] = credentials.secret_key
    os.environ[AWS_REGION] = session.region_name
    return session
