from abc import abstractmethod

from tfx.orchestration import metadata
from tfx.orchestration import pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

beam_pipeline_args = [
    '--direct_running_mode=multi_processing',
    '--direct_num_workers=0',
]


class BasePipeline:
    def __init__(self):
        pass

    def run(self, datasource):
        step_list = self.connect(datasource)
        component_list = []
        for step in step_list:
            component_list.append(
                step.to_component_class()(**step.inputs,
                                          **step.params))

        created_pipeline = pipeline.Pipeline(
            pipeline_name='pipeline_name',
            pipeline_root='/home/baris/Maiot/zenml/local_test/new_zenml/',
            components=component_list,
            enable_cache=False,
            metadata_connection_config=metadata.sqlite_metadata_connection_config('/home/baris/Maiot/zenml/local_test/new_zenml/db'),
            beam_pipeline_args=beam_pipeline_args)

        LocalDagRunner().run(created_pipeline)

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass
