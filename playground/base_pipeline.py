from abc import abstractmethod

from tfx.dsl.components.common.importer import Importer
from tfx.orchestration import metadata
from tfx.orchestration import pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from playground.artifacts import DataArtifact

beam_pipeline_args = [
    '--direct_running_mode=multi_processing',
    '--direct_num_workers=0',
]


class BasePipeline:
    def __init__(self):
        pass

    def run(self, datasource):
        data = Importer(
            source_uri="/home/baris/Maiot/zenml/local_test/data/data.csv",
            artifact_type=DataArtifact).with_id("datasource")

        step_list = [data] + [s.get_component() for s in
                              self.connect(data.outputs.result)]

        created_pipeline = pipeline.Pipeline(
            pipeline_name='pipeline_name',
            pipeline_root='/home/baris/Maiot/zenml/local_test/new_zenml/',
            components=step_list,
            enable_cache=False,
            metadata_connection_config=metadata.sqlite_metadata_connection_config(
                '/home/baris/Maiot/zenml/local_test/new_zenml/db'),
            beam_pipeline_args=beam_pipeline_args)

        LocalDagRunner().run(created_pipeline)

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass
