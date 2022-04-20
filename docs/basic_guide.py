

def build_a_pipeline():
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

