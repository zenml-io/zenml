#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from pipelines.facets_pipeline.facets_pipeline import facets_pipeline
from steps.evaluator.evaluator_step import evaluator
from steps.importer.importer_step import importer
from steps.trainer.trainer_step import trainer

from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)
from zenml.post_execution import get_pipeline


def visualize_statistics():
    pipe = get_pipeline(pipeline="facets_pipeline")
    importer_outputs = pipe.runs[0].get_step(step="importer")
    FacetStatisticsVisualizer().visualize(importer_outputs)


if __name__ == "__main__":
    # Run the pipeline
    pipeline_instance = facets_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluator(),
    )
    pipeline_instance.run()

    visualize_statistics()
