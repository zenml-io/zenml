

def getting_started_with_a_pipeline():
    from zenml.steps import step, Output
    from zenml.pipelines import pipeline

    @step
    def my_first_step() -> Output(output_int=int, output_float=float):
        """Step that returns a pre-defined integer and float"""
        return 7, 0.1


    @step
    def my_second_step(input_int: int, input_float: float
                       ) -> Output(output_int=int, output_float=float):
        """Step that doubles the inputs"""
        return 2 * input_int, 2* input_float


    @pipeline
    def first_pipeline(
        step_1,
        step_2
    ):
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

    first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()


def configure_at_runtime():
    from zenml.steps import step, Output, BaseStepConfig
    from zenml.pipelines import pipeline

    @step
    def my_first_step() -> Output(output_int=int, output_float=float):
        """Step that returns a pre-defined integer and float"""
        return 7, 0.1

    class SecondStepConfig(BaseStepConfig):
        """Trainer params"""
        multiplier: int = 4

    @step
    def my_second_step(config: SecondStepConfig, input_int: int,
                       input_float: float
                       ) -> Output(output_int=int, output_float=float):
        """Step that multiplie the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float

    @pipeline
    def first_pipeline(
            step_1,
            step_2
    ):
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step(SecondStepConfig(multiplier=3))
                   ).run(run_name="custom_pipeline_run_name")


def interact_with_completed_runs():
    from zenml.repository import Repository

    repo = Repository()
    pipelines = repo.get_pipelines()

    # now you can get pipelines by index
    pipeline_x = pipelines[-1]

    # all runs of a pipeline chronlogically ordered
    runs = pipeline_x.runs

    # get the last run by index
    run = runs[-1]

    # all steps of a pipeline
    steps = run.steps
    step = steps[0]
    print(step.entrypoint_name)

    # The outputs of a step, if there are multiple outputs they are accessible by name
    output = step.outputs["output_int"]

    # will get you the value from the original materializer used in the pipeline
    output.read()

