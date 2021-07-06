import inspect
from abc import abstractmethod


class BaseStep:
    def __init__(self):
        pass

    def __call__(self, **kwargs):
        # infer the input artifacts
        self.inputs = inspect.func(self.process)
        # infer the output artifacts
        self.outputs = self.outputs or self.output()
        return self

    @abstractmethod
    def process(self):
        pass

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
