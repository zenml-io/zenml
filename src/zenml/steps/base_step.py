import inspect
from abc import abstractmethod

from zenml.annotations import Input, Output, Param
from zenml.steps.utils import generate_component
from zenml.utils.exceptions import StepInterfaceError


class MultiOutput:
    # TODO: to be implemented
    pass


class BaseStepMeta(type):
    """ """

    def __new__(mcs, name, bases, dct):
        """ """
        # Setting up the class
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()
        cls.PARAM_DEFAULTS = dict()
        cls.OUTPUT_SPEC = dict()
        cls.OUTPUT_WRITERS = dict()

        # Looking into the signature of the provided process function
        process_spec = inspect.getfullargspec(cls.get_executable())
        process_args = process_spec.args

        # Remove the self from the signature if it exists
        if process_args and process_args[0] == "self":
            process_args.pop(0)

        # Parse the input signature of the function
        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                cls.INPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                cls.PARAM_SPEC.update({arg: arg_type.type})
            else:
                raise StepInterfaceError(
                    f"Unsupported or unknown annotation detected in the input "
                    f"signature {arg_type}. When designing your step please "
                    f"use either Input[AnyArtifact] or Param[AnyParam] for "
                    f"annotating your input signature."
                )

        # Infer the defaults
        process_defaults = process_spec.defaults
        if process_defaults is not None:
            for i, default in enumerate(process_defaults):
                # TODO: [HIGH] fix the implementation
                process_args.reverse()
                arg = process_args[i]
                arg_type = process_spec.annotations.get(arg, None)
                if not isinstance(arg_type, Param):
                    raise StepInterfaceError(
                        f"A default value in the signature of a step can only "
                        f"be used for a Param[...] not {arg_type}."
                    )

        # Parse the output annotations
        return_spec = process_spec.annotations.get("return", None)
        if return_spec is not None:
            # TODO: we can put the entire inference into a single function
            if issubclass(type(return_spec), MultiOutput):
                # TODO: the multi-output support will be added later
                pass
            else:
                if issubclass(type(return_spec), Output):
                    cls.OUTPUT_WRITERS.update({"output": type(return_spec)})
                    cls.OUTPUT_SPEC.update({"output": return_spec.type})
                else:
                    writer_type = infer_writer_type(return_spec)
                    artifact_type = infer_artifact_type(return_spec)
                    cls.OUTPUT_WRITERS.update({"output": writer_type})
                    cls.OUTPUT_SPEC.update({"output": artifact_type})

        return cls


class BaseStep(metaclass=BaseStepMeta):
    """ """

    def __init__(self, *args, **kwargs):
        self.__component = None
        self.__params = dict()

        if args:
            raise StepInterfaceError(
                "When you are creating an instance of a step, please only "
                "use key-word arguments."
            )

        for k, v in kwargs.items():
            assert k in self.PARAM_SPEC
            try:
                self.__params[k] = self.PARAM_SPEC[k](v)
            except TypeError or ValueError:
                raise StepInterfaceError("")

    def __call__(self, **artifacts):
        self.__component = generate_component(self)(
            **artifacts, **self.__params
        )
        # todo: multiple outputs
        return list(self.__component.outputs.values())[0]

    @abstractmethod
    def process(self, *args, **kwargs):
        """

        Args:
          *args:
          **kwargs:

        Returns:

        """

    def get_component(self):
        """ """
        return self.__component

    @classmethod
    def get_executable(cls):
        """ """
        return cls.process


# TODO: [LOW] find a more elegant solution to the lookup tables
def infer_artifact_type(obj):
    import pandas as pd

    if issubclass(obj, pd.DataFrame):
        from zenml.artifacts.data_artifacts.pandas_artifact import (
            PandasArtifact,  # isort: skip
        )

        return PandasArtifact
    elif issubclass(obj, (int, float, str)):
        from zenml.artifacts.data_artifacts.json_artifact import JSONArtifact

        return JSONArtifact


def infer_writer_type(obj):
    import pandas as pd

    if issubclass(obj, pd.DataFrame):
        from zenml.annotations.artifact_annotations import PandasOutput

        return PandasOutput
    elif issubclass(obj, (int, float, str)):
        from zenml.annotations.artifact_annotations import JSONOutput

        return JSONOutput
