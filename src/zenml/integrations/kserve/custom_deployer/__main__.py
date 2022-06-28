#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from pathlib import Path
from typing import Optional

import click
import kserve

from zenml.integrations.kserve.custom_deployer import ZenMLCustomModel

DEFAULT_MODEL_NAME = "model"
DEFAULT_LOCAL_MODEL_DIR = "/tmp/model"


@click.command()
@click.option(
    "--model_name",
    default=DEFAULT_LOCAL_MODEL_DIR,
    required=True,
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=Path
    ),
    help="The directory where the model is stored locally.",
)
@click.option(
    "--model_dir",
    default=DEFAULT_MODEL_NAME,
    required=True,
    type=click.STRING,
    help="The name of the model to deploy.",
)
@click.option(
    "--predict_func",
    required=True,
    type=click.STRING,
    help="The path to the predict function.",
)
@click.option(
    "--load_func",
    required=False,
    type=click.STRING,
    help="The path to the load function.",
)
def main(
    model_name: str, model_uri: str, predict_func: str, load_func: Optional[str]
):
    model = ZenMLCustomModel(model_name, model_uri, predict_func, load_func)
    model.load()
    kserve.ModelServer().start([model])


if __name__ == "__main__":
    main()
