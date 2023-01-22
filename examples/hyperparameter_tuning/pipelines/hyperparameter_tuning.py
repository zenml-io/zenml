from itertools import chain
from typing import Any, List, Type

from dynamic_pipelines.dynamic_pipeline import DynamicPipeline
from steps.data.split_data import split_data as split_data_step
from steps.evaluation.compare_scores import (
    CompareScoreParams,
    ReduceType,
    compare_score,
)
from steps.evaluation.evaluation_parameters import EvaluationParams

from zenml.steps import BaseParameters, BaseStep


def param_id(parameters: BaseParameters) -> str:
    return "_".join([str(x) for x in parameters.dict().values()])


class HyperParameterTuning(DynamicPipeline):
    """Generates the steps of the hyperparameter tuning pipeline dynamically based on the input, and connects
    the steps."""

    def __init__(
        self,
        load_data_step: Type[BaseStep],
        train_and_predict_step: Type[BaseStep],
        train_and_predict_best_model_step: Type[BaseStep],
        evaluate_step: Type[BaseStep],
        hyperparameters_conf_list: List[BaseParameters],
        **kwargs: Any,
    ) -> None:
        """

        Args:
            load_data_step: the type of step that loads the data.
            train_and_predict_step: the type of step that preforms training over the
                train data and returns the predictions over the test data, based on model
                parameters provided as steps parameters.
            train_and_predict_best_model_step: the type of step that preforms training over the
                train data and returns the predictions over the test data, based on model
                parameters provided as input to the step.
            evaluate_step: the type of step that evaluates a model.
            hyperparameters_conf_list: a list of `BaseParameters`, which will be given as input
                to the model's constructor.
        """
        self.load_data_step = load_data_step()
        self.split_test = split_data_step().configure(name="split_train_test")
        self.tuning_steps = [
            (
                split_data_step().configure(
                    name=f"split_train_validation_{param_id(param)}"
                ),
                train_and_predict_step(param).configure(
                    name=f"{train_and_predict_step.__name__}_{param_id(param)}"
                ),
                evaluate_step(
                    EvaluationParams(
                        model_parameters=dict(param),
                        evaluation_type="validation",
                    )
                ).configure(name=f"{evaluate_step.__name__}_{param_id(param)}"),
            )
            for param in hyperparameters_conf_list
        ]

        self.compare_scores = compare_score(
            CompareScoreParams(
                reduce=ReduceType.MAX,
                output_steps_names=[
                    steps[-1].name for steps in self.tuning_steps
                ],
            )
        )

        self.train_and_predict_best_model = train_and_predict_best_model_step()
        self.evaluate_best = evaluate_step(
            EvaluationParams(evaluation_type="best model evaluation")
        )

        super().__init__(
            self.load_data_step,
            self.split_test,
            self.compare_scores,
            self.train_and_predict_best_model,
            self.evaluate_best,
            *chain.from_iterable(self.tuning_steps),
            **kwargs,
        )

    def connect(self, **kwargs: BaseStep) -> None:
        """
        The method connects the input and outputs of the hyperparameter tuning pipeline.

        Args:
            **kwargs: the step instances of the pipeline.
        """
        X, y = self.load_data_step()
        X_train_val, X_test, y_train_val, y_test = self.split_test(X, y)
        for split_validation, train_and_predict, evaluate in self.tuning_steps:
            X_train, X_val, y_train, y_val = split_validation(
                X_train_val, y_train_val
            )
            y_pred = train_and_predict(X_train, y_train, X_val)
            evaluate(y_val, y_pred)
            self.compare_scores.after(evaluate)

        best_model_parameters = self.compare_scores()
        y_pred = self.train_and_predict_best_model(
            best_model_parameters, X_train_val, y_train_val, X_test
        )
        self.evaluate_best(y_test, y_pred)
