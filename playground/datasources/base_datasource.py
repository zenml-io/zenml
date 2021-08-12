from tfx.dsl.components.common.importer import Importer


class BaseDatasource:
    DS_TYPE = None

    def __init__(self, uri, *args, **kwargs):
        self.uri = uri

        self.__component = self.get_component()

    def __getattr__(self, item):
        if item == "outputs":
            return self.__component.outputs
        else:
            raise AttributeError

    def get_component(self):
        return Importer(source_uri=self.uri,
                        artifact_type=self.DS_TYPE)
