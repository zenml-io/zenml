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

import glob
import os
from pathlib import Path
from typing import Dict

from zenml.steps import BaseParameters, Output, step
from zenml.steps.step_context import StepContext


class LoadTextDataParameters(BaseParameters):
    base_path = str(
        Path(__file__).parent.absolute().parent.absolute() / "data"
    )
    dir_name = "batch_1"


@step(enable_cache=True)
def load_text_data(
    params: LoadTextDataParameters,
    context: StepContext,
) -> Output(images=Dict, uri=str):
    """Gets texts from a cloud artifact store directory."""
    text_dir_path = os.path.join(params.base_path, params.dir_name)
    text_files = glob.glob(f"{text_dir_path}/*.txt")
    uri = context.get_output_artifact_uri("images")

    texts = {}
    for i, text_file in enumerate(text_files):
        with open(text_file, "r", encoding="utf-8") as file:
            text = file.readlines()[0]
        artifact_filepath = f"{uri}/1/{i}/text.txt"

        texts[artifact_filepath] = text
    return texts, uri
