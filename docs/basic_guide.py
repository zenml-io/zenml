

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
        """Step that multiply the inputs"""
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

    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step()
                   ).with_config("config.yml").run()


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


def caching_and_zenml():
    from zenml.steps import step, Output, BaseStepConfig
    from zenml.pipelines import pipeline

    @step
    def my_first_step() -> Output(output_int=int, output_float=float):
        """Step that returns a pre-defined integer and float"""
        return 7, 0.1

    @step(enable_cache=False)
    def my_second_step(input_int: int, input_float: float
                       ) -> Output(output_int=int, output_float=float):
        """Step that doubles the inputs"""
        return 2 * input_int, 2 * input_float

    class SecondStepConfig(BaseStepConfig):
        """Trainer params"""
        multiplier: int = 4

    @step
    def my_configured_step(config: SecondStepConfig, input_int: int,
                           input_float: float
                           ) -> Output(output_int=int, output_float=float):
        """Step that multiply the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float

    @pipeline
    def first_pipeline(
            step_1,
            step_2
    ):
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step()
                   ).run()

    # Step one will use cache, Step two will be rerun due to decorator config
    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step()
                   ).run()

    # Complete pipeline will be rerun
    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step()
                   ).run(enable_cache=False)

    first_pipeline(step_1=my_first_step(),
                   step_2=my_configured_step(SecondStepConfig(multiplier=11))
                   ).run()

    # Step one will use cache, Step two is rerun as the config changed
    first_pipeline(step_1=my_first_step(),
                   step_2=my_configured_step(SecondStepConfig(multiplier=13))
                   ).run()


def fetching_historic_runs():
    from random import randint
    from zenml.steps import step, Output, StepContext
    from zenml.pipelines import pipeline

    @step
    def my_first_step() -> Output(output_int=int, output_float=float):
        """Step that returns a pre-defined integer and float"""
        return 7, 0.1

    @step(enable_cache=False)
    def my_second_step(
            input_int: int, input_float: float
    ) -> Output(multiplied_output_int=int, multiplied_output_float=float):
        """Step that doubles the inputs"""
        multiplier = randint(0, 100)
        return multiplier * input_int, multiplier * input_float

    @step
    def my_third_step(context: StepContext, input_int: int) -> bool:
        """Step that decides if this pipeline run produced the highest value
        for `input_int`"""
        highest_int = 0

        # Inspect all past runs of `first_pipeline`
        try:
            pipeline_runs = (context.metadata_store
                                    .get_pipeline("first_pipeline")
                                    .runs)
        except KeyError:
            # If this is the first time running this pipeline you don't want
            #  it to fail
            print('No previous runs found, this run produced the highest '
                  'number by default.')
            return True
        else:
            for run in pipeline_runs:
                # get the output of the second step
                try:
                    multiplied_output_int = (run.get_step("step_2")
                                                .outputs['multiplied_output_int']
                                                .read())
                except KeyError:
                    # If you never ran the pipeline or ran it with steps that
                    #  don't produce a step with the name
                    #  `multiplied_output_int` then you don't want this to fail
                    pass
                else:
                    if multiplied_output_int > highest_int:
                        highest_int = multiplied_output_int

        if highest_int > input_int:
            print('Previous runs produced a higher number.')
            return False  # There was a past run that produced a higher number
        else:
            print('This run produced the highest number.')
            return True  # The current run produced the highest number

    @pipeline
    def first_pipeline(
        step_1,
        step_2,
        step_3
    ):
        output_1, output_2 = step_1()
        output_1, output_2 = step_2(output_1, output_2)
        is_best_run = step_3(output_1)

    first_pipeline(step_1=my_first_step(),
                   step_2=my_second_step(),
                   step_3=my_third_step()).run()

configure_at_runtime()