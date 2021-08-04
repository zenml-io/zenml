"""
The implementation of the set of GenericType and GenericMeta class below is
inspired by the implementation by the Tensorflow Extended team, which can be
found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/annotations.py

The list of changes to improve the interaction with ZenML:

- The main classes are merged into a single class which serves as the base
class to be extended
- A class variable is added to be utilized while checking the type of T
- A few more classes are created on top of artifacts and primitives in order to
use the same paradigm with steps and datasources as well

"""
import inspect
from typing import Type

from six import with_metaclass

from playground.artifacts.base_artifact import BaseArtifact
from playground.datasources.base_datasource import BaseDatasource
from playground.steps.base_step import BaseStep


class GenericMeta(type):
    def __getitem__(cls: Type["GenericType"],
                    params):
        return cls._generic_getitem(params)


class GenericType(with_metaclass(GenericMeta, object)):
    """A main generic class which will be used as the base for annotations"""
    VALID_TYPES = None

    def __init__(self,
                 object_type,
                 _init_via_getitem=False):

        if not _init_via_getitem:
            class_name = self.__class__.__name__
            raise ValueError(f"{class_name} should be instantiated via %s[T], "
                             f"where T is one of {self.VALID_TYPES}")
        self.type = object_type

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self.type)

    @classmethod
    def _generic_getitem(cls, params):
        if inspect.isclass(params) and \
                any(issubclass(params, t) for t in cls.VALID_TYPES):
            return cls(params, _init_via_getitem=True)
        else:
            class_name = cls.__name__
            raise ValueError(f"Generic type `{class_name}[T]` expects the "
                             f"single parameter T to be one of "
                             f"{cls.VALID_TYPES}.")


Datasource = type("Datasource",
                  (GenericType,),
                  {"VALID_TYPES": [BaseDatasource]})

Step = type("Step",
            (GenericType,),
            {"VALID_TYPES": [BaseStep]})

Input = type("Input",
             (GenericType,),
             {"VALID_TYPES": [BaseArtifact]})

Output = type("Output",
              (GenericType,),
              {"VALID_TYPES": [BaseArtifact]})

Param = type("Param",
             (GenericType,),
             {"VALID_TYPES": [int, float, str, bytes]})
