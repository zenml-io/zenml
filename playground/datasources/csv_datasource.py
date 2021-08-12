from playground.artifacts.data_artifacts import CSVArtifact
from playground.datasources.base_datasource import BaseDatasource


class CSVDatasource(BaseDatasource):
    DS_TYPE = CSVArtifact
