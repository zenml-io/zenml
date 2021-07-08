import inspect
from abc import abstractmethod

from tfx.dsl.component.experimental.decorators import component

from playground.artifacts import Input, Output
from playground.exceptions import StepInterfaceError


class StepDict(dict):
    __getattr__ = dict.__getitem__


class BaseStep:
    def __init__(self):
        self.__inputs = StepDict()
        self.__outputs = StepDict()
        self.__params = StepDict()

    def __call__(self, **kwargs):
        process_spec = inspect.getfullargspec(self.process)
        instance_spec = inspect.getfullargspec(self.__init__)

        # TODO: check whether it is implemented as a static or class method
        # TODO: implement a way to interpret the params

        if instance_spec.varkw is not None:
            raise StepInterfaceError(
                "As ZenML aims to track all the configuration parameters "
                "that you provide to your steps, please refrain from using "
                "a non-descriptive parameter definition such as '*args'.")

        if instance_spec.varkw is not None:
            raise StepInterfaceError(
                "As ZenML aims to track all the configuration parameters "
                "that you provide to your steps, please refrain from using "
                "a non-descriptive parameter definition such as '**kwargs'.")

        for arg in instance_spec.args:
            if arg == 'self':  # TODO: not covering all the cases
                continue

        for arg, arg_type in process_spec.annotations.items():
            if isinstance(arg_type, Input):
                if arg in kwargs:
                    self.__inputs.update({arg: kwargs[arg]})
                else:
                    self.__inputs.update({arg: arg_type.type()})
            elif isinstance(arg_type, Output):
                if arg in kwargs:
                    raise StepInterfaceError(
                        "While connecting steps to each other, please avoid "
                        "using predefined output artifacts.")
                else:
                    self.__outputs.update({arg: arg_type.type()})
            else:
                raise StepInterfaceError(
                    "While designing the 'process' function of your steps, "
                    "you can only use Input[Artifact] or Output[Artifact] "
                    "types as input. In order to define parameters, please "
                    "use the __init__ function.")

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    @property
    def inputs(self):
        return self.__inputs

    @property
    def outputs(self):
        return self.__outputs

    @property
    def params(self):
        return self.__params

    @inputs.setter
    def inputs(self, inputs):
        raise PermissionError('The attribute inputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @outputs.setter
    def outputs(self, outputs):
        raise PermissionError('The attribute outputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @params.setter
    def params(self, params):
        raise PermissionError('The attribute params is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @inputs.deleter
    def inputs(self):
        self.__inputs = StepDict()

    @outputs.deleter
    def outputs(self):
        self.__outputs = StepDict()

    @params.deleter
    def params(self):
        self.__params = StepDict()

    def to_component(self):
        return component(self.process(**self.inputs, **self.outputs))

    # class DistributedBaseStep:
    #     def __init__(self):
    #         pass
    #
    #     def __call__(self, **kwargs):
    #         self.inputs = inspect.func(self.process)
    #         self.outputs = self.outputs or self.output()
    #         return self
    #
    #     def process(self):
    #         with beam.pipeline() as p:
    #             (p | ReadParDo | ProcessParDo | WriteParDo)
    #
    #     def ReadParDo(self):
    #         with self._make_beam_pipeline():
    #             return p | beam.io.ReadFromArrow(self.data.uri)
    #
    #     def ProcessParDo(self):
    #         pass
    #
    #     def WriteParDo(self):
    #         pass
    #
    #     def process(self,
    #                 data: DataArtifact,
    #                 schema: SchemaArtifact,
    #                 statistics: StatisticsArtifact
    #                 ) -> PandasDataFrameArtifact:
    #         t = PandasDataFrameArtifact()
    #
    #         return t
