from abc import abstractmethod
import inspect
from playground.artifacts.base_artifact import BaseArtifact
from playground.utils.annotations import GenericType
from playground.utils.exceptions import DatasourceInterfaceError

Output = type("Output",
              (GenericType,),
              {"VALID_TYPES": [BaseArtifact]})

Param = type("Param",
             (GenericType,),
             {"VALID_TYPES": [int, float, str, bytes, dict]})


class BaseDatasourceMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        cls.OUTPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()
        cls.PARAM_DEFAULTS = dict()  # TODO: handle defaults

        ingest_spec = inspect.getfullargspec(cls.process)
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
        self.__params = dict()
        self.__datasources = dict()

        if args:
            raise DatasourceInterfaceError("")  # TODO: Fill

        for k, v in kwargs.items():
            if k in self.PARAM_SPEC:
                self.__params.update({k: v})
            else:
                raise DatasourceInterfaceError("")  # TODO: Fill

    @abstractmethod
    def ingest(self, *args, **kwargs):
        pass

    def run(self):
        pass
