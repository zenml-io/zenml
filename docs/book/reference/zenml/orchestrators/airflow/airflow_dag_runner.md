Module zenml.orchestrators.airflow.airflow_dag_runner
=====================================================
Definition of Airflow TFX runner. This is an unmodified  copy from the TFX
source code (outside of superficial, stylistic changes)

Classes
-------

`AirflowDagRunner(config: Union[Dict[str, Any], zenml.orchestrators.airflow.airflow_dag_runner.AirflowPipelineConfig, NoneType] = None)`
:   Tfx runner on Airflow.
    
    Creates an instance of AirflowDagRunner.
    
    Args:
      config: Optional Airflow pipeline config for customizing the
      launching of each component.

    ### Ancestors (in MRO)

    * tfx.orchestration.tfx_runner.TfxRunner
    * abc.ABC

    ### Methods

    `run(self, tfx_pipeline: tfx.orchestration.pipeline.Pipeline)`
    :   Deploys given logical pipeline on Airflow.
        
        Args:
          tfx_pipeline: Logical pipeline containing pipeline args and comps.
        
        Returns:
          An Airflow DAG.

`AirflowPipelineConfig(airflow_dag_config: Optional[Dict[str, Any]] = None, **kwargs)`
:   Pipeline config for AirflowDagRunner.
    
    Creates an instance of AirflowPipelineConfig.
    Args:
      airflow_dag_config: Configs of Airflow DAG model. See
        https://airflow.apache.org/_api/airflow/models/dag/index.html#airflow.models.dag.DAG
          for the full spec.
      **kwargs: keyword args for PipelineConfig.

    ### Ancestors (in MRO)

    * tfx.orchestration.config.pipeline_config.PipelineConfig