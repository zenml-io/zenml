import inspect
import types
from abc import abstractmethod
from typing import Type

from tfx.orchestration import metadata
from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from playground.utils.annotations import Step, Datasource
from playground.utils.exceptions import PipelineInterfaceError


class DictWrapper(dict):
    def __getattr__(self, name):
        return self[name]


class BasePipeline:

    def __init__(self, *args, **kwargs):
        if args:
            raise PipelineInterfaceError()  # TODO

        self.__pipeline = None
        self.__steps = dict()
        self.__datasources = dict()

        self.__step_spec = dict()
        self.__datasource_spec = dict()

        connect_spec = inspect.getfullargspec(self.connect)
        connect_args = connect_spec.args
        connect_args.pop(0)  # Remove the self
        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            if isinstance(arg_type, Step):
                self.__step_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Datasource):
                self.__datasource_spec.update({arg: arg_type.type})
            else:
                raise PipelineInterfaceError("")  # TODO: fill

        for k, v in kwargs.items():
            assert k in self.__step_spec or k in self.__datasource_spec

            if k in self.__step_spec:
                # TODO: assert issubclass(v, self.__step_spec[k])
                self.__steps.update({k: v})
            elif k in self.__datasource_spec:
                self.__datasources.update({k: v})
            else:
                raise PipelineInterfaceError("")

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass

    def run(self):
        from tfx.dsl.components.common.importer import Importer
        from playground.artifacts.data_artifacts import CSVArtifact

        data = Importer(
            source_uri="/home/baris/Maiot/zenml/local_test/data",
            artifact_type=CSVArtifact).with_id("datasource")

        self.connect(datasource=data.outputs.result, **self.__steps)

        step_list = [data] + \
                    [s.get_component() for s in self.__steps.values()]

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name='pipeline_name',
            pipeline_root='/home/baris/Maiot/zenml/local_test/new_zenml/',
            components=step_list,
            enable_cache=False,
            metadata_connection_config=metadata.sqlite_metadata_connection_config(
                '/home/baris/Maiot/zenml/local_test/new_zenml/db'),
            beam_pipeline_args=[
                '--direct_running_mode=multi_processing',
                '--direct_num_workers=0'])

        LocalDagRunner().run(created_pipeline)


def pipeline(func: types.FunctionType) -> Type:
    pipeline_class = type(func.__name__,
                          (BasePipeline,),
                          {})
    pipeline_class.connect = func
    return pipeline_class
