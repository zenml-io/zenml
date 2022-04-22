

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
        return 2 * input_int, 2 * input_float


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


def how_data_flows_through_steps():
    import os
    from typing import Type

    from zenml.steps import step
    from zenml.pipelines import pipeline

    from zenml.artifacts import DataArtifact
    from zenml.io import fileio
    from zenml.materializers.base_materializer import BaseMaterializer

    class MyObj:
        def __init__(self, name: str):
            self.name = name

    class MyMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = (MyObj,)
        ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

        def handle_input(self, data_type: Type[MyObj]) -> MyObj:
            """Read from artifact store"""
            super().handle_input(data_type)
            with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                             'r') as f:
                name = f.read()
            return MyObj(name=name)

        def handle_return(self, my_obj: MyObj) -> None:
            """Write to artifact store"""
            super().handle_return(my_obj)
            with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                             'w') as f:
                f.write(my_obj.name)

    @step
    def my_first_step() -> MyObj:
        """Step that returns an object of type MyObj"""
        return MyObj("my_object")

    @step
    def my_second_step(my_obj: MyObj) -> None:
        """Step that prints the input object and returns nothing."""
        print(f"The following object was passed to this step: `{my_obj.name}`")

    @pipeline
    def first_pipeline(
        step_1,
        step_2
    ):
        output_1 = step_1()
        step_2(output_1)

    first_pipeline(
        step_1=my_first_step().with_return_materializers(MyMaterializer),
        step_2=my_second_step()).run()
