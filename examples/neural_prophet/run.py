#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from pipelines.neural_prophet_pipeline.neural_prophet_pipeline import (
    neural_prophet_pipeline,
)
from steps.data_loader.data_loader_step import data_loader
from steps.predictor.predictor_step import predictor
from steps.trainer.trainer_step import trainer

if __name__ == "__main__":
    pipeline = neural_prophet_pipeline(
        data_loader=data_loader(), trainer=trainer(), predictor=predictor()
    )

    pipeline.run()

    print(
        "Pipeline has run and model is trained. Please run the "
        "`post_execution.ipynb` notebook to inspect the results."
    )
