from zenml.integrations.constants import SKLEARN
from zenml.pipelines import pipeline


@pipeline(required_integrations=[SKLEARN])
def digits_pipeline(importer, trainer, evaluator):
    """Links all the steps together in a pipeline"""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)
