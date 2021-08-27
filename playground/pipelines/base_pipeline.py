import inspect
from abc import abstractmethod

from tfx.orchestration import metadata
from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from playground.annotations.step_annotations import Step
from playground.utils.exceptions import PipelineInterfaceError


class BasePipelineMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        cls.STEP_SPEC = dict()

        connect_spec = inspect.getfullargspec(cls.connect)
        connect_args = connect_spec.args

        if connect_args and connect_args[0] == "self":
            connect_args.pop(0)

        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            if isinstance(arg_type, Step):
                cls.STEP_SPEC.update({arg: arg_type.type})
            else:
                raise PipelineInterfaceError("")  # TODO: fill message
        return cls


class BasePipeline(metaclass=BasePipelineMeta):
    def __init__(self, *args, **kwargs):
        self.__steps = dict()

        if args:
            raise PipelineInterfaceError("")  # TODO: Fill

        for k, v in kwargs.items():
            if k in self.STEP_SPEC:
                self.__steps.update({k: v})  # TODO: assert class
            else:
                raise PipelineInterfaceError("")  # TODO: Fill

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass

    def run(self):
        self.connect(**self.__steps)

        step_list = [s.get_component() for s in self.__steps.values()]

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name="pipeline_name",
            pipeline_root="/home/baris/Maiot/zenml/local_test/new_zenml/",
            components=step_list,
            enable_cache=False,
            metadata_connection_config=metadata.sqlite_metadata_connection_config(
                "/home/baris/Maiot/zenml/local_test/new_zenml/db"
            ),
            beam_pipeline_args=[
                "--direct_running_mode=multi_processing",
                "--direct_num_workers=0",
            ],
        )

        LocalDagRunner().run(created_pipeline)

