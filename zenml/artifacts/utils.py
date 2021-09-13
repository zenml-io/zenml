class WriterFactory:

    def __init__(self):
        self.types = {}

    def get_types(self):
        return self.types

    def get_single_type(self, key):
        return self.types[key]

    def register_type(self, key, type_):
        self.types[key] = type_


