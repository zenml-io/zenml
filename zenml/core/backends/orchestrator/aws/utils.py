import base64
import json
from typing import Dict, Text
from zenml.utils.constants import ZENML_BASE_IMAGE_NAME, AWS_ENTRYPOINT


def _get_container_params(config):
    config_encoded = base64.b64encode(json.dumps(config).encode())
    return f'python -m {AWS_ENTRYPOINT} run_pipeline --config_b64 ' \
           f'{config_encoded.decode()}'


def get_startup_script(config: Dict,
                       zenml_image: Text = ZENML_BASE_IMAGE_NAME):
    c_params = _get_container_params(config)
    return f"#!/bin/bash\n" \
           f"sudo HOME=/home/root docker run --net=host {zenml_image} {c_params}"
