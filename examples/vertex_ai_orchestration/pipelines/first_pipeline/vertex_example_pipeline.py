from zenml.pipelines import pipeline


@pipeline
def vertex_example_pipeline(first_step, second_step, third_step):
    # Link all the steps artifacts together
    first_num = first_step()
    random_num = second_step()
    third_step(first_num, random_num)
