import inspect
from abc import abstractmethod

from tfx.orchestration import metadata
from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from playground.annotations.artifact_annotations import Output, Param
from playground.utils.exceptions import DatasourceInterfaceError
from playground.utils.step_utils import generate_component


class BaseDatasourceMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()
        cls.OUTPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()
        cls.PARAM_DEFAULTS = dict()  # TODO: handle defaults

        ingest_spec = inspect.getfullargspec(cls.get_executable())
        ingest_args = ingest_spec.args

        if ingest_args and ingest_args[0] == "self":
            ingest_args.pop(0)

        for arg in ingest_args:
            arg_type = ingest_spec.annotations.get(arg, None)
            if isinstance(arg_type, Output):
                cls.OUTPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                cls.PARAM_SPEC.update({arg: arg_type.type})
            else:
                raise DatasourceInterfaceError("")  # TODO: fill message

        return cls


class BaseDatasource(metaclass=BaseDatasourceMeta):

    def __init__(self, *args, **kwargs):
        if args:
            raise DatasourceInterfaceError("")  # TODO: Fill

        self.__params = dict()
        for k, v in kwargs.items():
            assert k in self.PARAM_SPEC
            try:
                self.__params[k] = self.PARAM_SPEC[k](v)
            except TypeError or ValueError:
                raise DatasourceInterfaceError("")

        self.__component = generate_component(step=self)(**self.__params)

    def __getattr__(self, item):
        if item == "outputs":
            return self.__component.outputs # TODO: Here is the problem
        else:
            raise AttributeError(f"{item}")

    @abstractmethod
    def ingest(self, *args, **kwargs):
        pass

    def commit(self):
        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name='pipeline_name',
            pipeline_root='/home/baris/Maiot/zenml/local_test/new_zenml/',
            components=[self.get_component()],
            enable_cache=False,
            metadata_connection_config=metadata.sqlite_metadata_connection_config(
                '/home/baris/Maiot/zenml/local_test/new_zenml/db'),
            beam_pipeline_args=[
                '--direct_running_mode=multi_processing',
                '--direct_num_workers=0'])

        LocalDagRunner().run(created_pipeline)

    def get_component(self):
        return self.__component

    @classmethod
    def get_executable(cls):
        return cls.ingest


