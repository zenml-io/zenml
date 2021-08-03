from playground.artifacts import DataArtifact, Input, Output, Param


@step
def SplitStep(input_data: Input[DataArtifact],
              output_data: Output[DataArtifact],
              split_map: Param[float]):
    input_data.read()

    output_data.write()
