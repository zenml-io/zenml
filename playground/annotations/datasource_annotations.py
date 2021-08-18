from playground.annotations.base_annotations import GenericType
from playground.datasources.base_datasource import BaseDatasource

Datasource = type("Datasource",
                  (GenericType,),
                  {"VALID_TYPES": [BaseDatasource]})
