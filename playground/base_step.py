import inspect
from abc import abstractmethod

from tfx.dsl.component.experimental.decorators import component

from playground.artifacts import Input, Output


class BaseStep:
    def __init__(self):
        self.__inputs = {}
        self.__outputs = {}

    def __call__(self, **kwargs):
        full_spec = inspect.getfullargspec(self.process)
        # TODO: Make a dot dict
        # TODO: check whether it is implemented as a static or class method
        # TODO: implement a way to interpret the params
        for arg, arg_type in full_spec.annotations.items():
            if isinstance(arg_type, Input):
                self.__inputs.update({arg: arg_type.type()})
            if isinstance(arg_type, Output):
                self.__outputs.update({arg: arg_type.type()})
        return self

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    @property
    def inputs(self):
        return self.__inputs

    @property
    def outputs(self):
        return self.__outputs

    @inputs.setter
    def inputs(self, inputs):
        raise PermissionError('The attribute inputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @outputs.setter
    def outputs(self, outputs):
        raise PermissionError('The attribute outputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @inputs.deleter
    def inputs(self):
        self.__inputs = dict()

    @outputs.deleter
    def outputs(self):
        self.__outputs = dict()

    def to_component(self):
        @component
        def Component(**kwargs):
            self.process(kwargs)

        return Component(**self.inputs, **self.outputs)

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
