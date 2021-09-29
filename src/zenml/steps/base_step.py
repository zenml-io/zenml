import inspect
from abc import abstractmethod

from zenml.annotations import Input, Output, Param
from zenml.steps.utils import generate_component
from zenml.utils.exceptions import StepInterfaceError


class BaseStepMeta(type):
    """ """

    def __new__(mcs, name, bases, dct):
        """ """
        # Setting up the class
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()
        cls.OUTPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()

        cls.PARAM_DEFAULTS = dict()

        # Looking into the signature of the provided process function
        process_spec = inspect.getfullargspec(cls.process)
        process_args = process_spec.args

        # Remove the self from the signature if it exists
        if process_args and process_args[0] == "self":
            process_args.pop(0)

        # Parse the input signature of the function
        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                cls.INPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                cls.OUTPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                cls.PARAM_SPEC.update({arg: arg_type.type})
            else:
                raise StepInterfaceError(
                    f"Unsupported or unknown annotation {arg_type} detected "
                    f"in the input signature . When designing your step "
                    f"please use either Input[AnyArtifactType], "
                    f"Output[AnyArtifactType] or Param[AnyPrimitiveType] for "
                    f"your annotations."
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

        return cls


class BaseStep(metaclass=BaseStepMeta):
    """ The base implementation of a ZenML Step which will be inherited by all
    the other step implementations
    """

    def __init__(self, *args, **kwargs):
        self.__component_class = generate_component(self)

        if args:
            raise StepInterfaceError(
                "When you are creating an instance of a step, please only "
                "use key-word arguments.")

        self.__component = None

        self.__inputs = dict()
        self.__params = dict()
        for k, v in kwargs.items():
            assert k in self.PARAM_SPEC
            try:
                self.__params[k] = self.PARAM_SPEC[k](v)
            except TypeError or ValueError:
                raise StepInterfaceError("")

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    @property
    def component(self):
        if self.__component is None:
            # TODO: [HIGH] Check whether inputs are provided
            return self.__component_class(**self.__inputs, **self.__params)
        else:
            return self.__component

    def set_inputs(self, **artifacts):
        self.__inputs.update(artifacts)

    def get_outputs(self):
        return self.component.outputs
