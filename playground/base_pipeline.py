from abc import abstractmethod


class BasePipeline:
    def __init__(self):
        pass

    def run(self):
        step_list = self.connect(None)
        component_list = []
        for step in step_list:
            component_list.append(step.to_component())

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass
