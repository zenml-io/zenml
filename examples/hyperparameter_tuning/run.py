from pipelines.hyperparameter_tuning import HyperParameterTuning
from steps.classifier.random_forest_classifier import (
    RandomForestClassifierParameters,
    train_and_predict_best_rf_classifier,
    train_and_predict_rf_classifier,
)
from steps.data.load_breast_cancer_data import load_breast_cancer_data
from steps.data.load_iris_data import load_iris_data
from steps.evaluation.accuracy import calc_accuracy

if __name__ == "__main__":
    HyperParameterTuning.as_template_of("iris_random_forest")(
        load_data_step=load_iris_data,
        train_and_predict_step=train_and_predict_rf_classifier,
        train_and_predict_best_model_step=train_and_predict_best_rf_classifier,
        evaluate_step=calc_accuracy,
        hyperparameters_conf_list=[
            RandomForestClassifierParameters(n_estimators=100),
            RandomForestClassifierParameters(n_estimators=200),
            RandomForestClassifierParameters(n_estimators=300),
            RandomForestClassifierParameters(n_estimators=400),
        ],
    ).run(enable_cache=False)

    HyperParameterTuning.as_template_of("breast_cancer_random_forest")(
        load_data_step=load_breast_cancer_data,
        train_and_predict_step=train_and_predict_rf_classifier,
        train_and_predict_best_model_step=train_and_predict_best_rf_classifier,
        evaluate_step=calc_accuracy,
        hyperparameters_conf_list=[
            RandomForestClassifierParameters(n_estimators=100),
            RandomForestClassifierParameters(n_estimators=100, max_depth=5),
            RandomForestClassifierParameters(
                n_estimators=100, criterion="entropy"
            ),
        ],
    ).run(enable_cache=False)
