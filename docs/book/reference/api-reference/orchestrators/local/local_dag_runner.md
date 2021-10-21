Module zenml.orchestrators.local.local_dag_runner
=================================================
Definition of Beam TFX runner. Inspired by local dag runner implementation
by Google at: https://github.com/tensorflow/tfx/blob/master/tfx/orchestration
/local/local_dag_runner.py

Functions
---------

    
`format_timedelta_pretty(seconds: float) ‑> str`
:   Format a float representing seconds into a string.
    
    Args:
      seconds: result of a time.time() - time.time().
    
    Returns:
        Pretty formatted string according to specification.

Classes
-------

`LocalDagRunner()`
:   Local TFX DAG runner.
    
    Initializes LocalDagRunner as a TFX orchestrator.

    ### Ancestors (in MRO)

    * tfx.orchestration.portable.tfx_runner.TfxRunner

    ### Methods

    `run(self, pipeline: tfx.orchestration.pipeline.Pipeline) ‑> None`
    :   Runs given logical pipeline locally.
        
        Args:
          pipeline: Logical pipeline containing pipeline args and components.