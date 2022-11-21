from zenml.pipelines import pipeline


@pipeline(
    enable_cache=False,
)
def neptune_example_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    """
    Link all the steps artifacts together
    """
    x_train, y_train, x_test, y_test = importer()
    x_trained_normed, x_test_normed = normalizer(x_train=x_train, x_test=x_test)
    model = trainer(x_train=x_trained_normed, y_train=y_train)
    evaluator(x_test=x_test_normed, y_test=y_test, model=model)
