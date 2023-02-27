# Grid search based Hyper-parameter tuning with Dynamic Pipelines

This example demonstrates the concept of a dynamic pipeline in ZenML. Dynamic pipelines do not necessarily have a fixed number of steps, but allow the user to define pipelines with a configurable amount of steps with splitting branches. The example shown here illustrates one such application of a dynamic pipeline, namely creating a pipeline that performs a grid search hyperparameter tuning all within one pipeline and on the orchestrator level.

Note, that this is not always the ideal way to perform hyperparameter tuning, however, it does illustrate one of the potential use-cases of using dynamic pipelines.

## Dynamic Pipelines

This is achieved by creating a pipeline class rather than using 
the decorator. The pipeline class should inherit from `DynamicPipeline` class (implemented in this example) rather 
than ZenML's `BasePipeline` class. 

```python
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
        Initialize the pipeline by creating the step instances used by it.

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

```

In the `__init__` method of the pipeline, all steps are initialized based on the pipeline's constructor 
arguments. For instance, in this example, the number of steps is dependent on the number of 
elements in `hyperparameters_conf_list` in order to create the split_validation, train, and evaluate steps for each 
hyperparameter configuration. Finally, the super constructor is called with all the steps required for the pipeline. 
The constructor of `DynamicPipeline` class initializes the `STEP_SPEC` field for the current pipeline class. 
Normally, this field is initialized by `BasePipelineMeta`, however, since the constructor of the pipeline does
not contain step instances, `STEP_SPEC` would not be initialized properly.
Notice that some names of the step instances are changed (using the `configure` method), as creating multiple steps 
with the same name in ZenML pipelines is not possible.

The `connect` method utilizes the parameters defined in the pipeline constructor to connect the steps
together, without having to rely on the step list or dictionary given as the method arguments. For instance, in the
`HyperParameterTuning` pipeline, the `connect` method uses the list of tuples of steps, containing the split_validation,
train and evaluate steps for each hyperparameter configuration. 

## Gather outputs from multiple steps

Another required utility not enabled out of the box in ZenML is the ability to gather outputs from multiple steps and
use them as inputs to another step. In the `HyperParameterTuning` pipeline, the `compare_scores` step should receive the
scores from all `evaluate` steps.

```python
@step
def compare_score(params: CompareScoreParams) -> dict:
    """Compare scores over multiple evaluation outputs."""
    outputs = EvaluationOutputParams.gather(params)

    if params.reduce == ReduceType.MIN:
        output = min(outputs, key=lambda x: x.score)
        print(
            f"minimal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters

    if params.reduce == ReduceType.MAX:
        output = max(outputs, key=lambda x: x.score)
        print(
            f"maximal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters
```

This is enabled with two kinds of parameters classes:
* `GatherStepsParameters` - define parameters to identify a group of steps (by step name prefix or by a list of step
names). In the `HyperParameterTuning` pipeline, `CompareScoreParams` inherits from `GatherStepsParameters` so it
contains both the parameters for the comparison of scores and the parameters to gather step outputs.
* `OutputParameters` - classes that inherit from this class will define the output parameters of a step. This class
implements the `gather` method which receives a `GatherStepsParameters` object. The method will gather all the output
values of the steps compatible with the `GatherStepsParameters` object, and return them as a collection of outputs of the 
concrete class inheriting from `OutputParameters`. For example, in the `HyperParameterTuning` pipeline,
`EvaluationOutputParams` defines all the output parameters expected from an evaluation step (e.g. calc_accuracy step).
The prefix of the evaluation steps will be passed to `CompareScoreParams`, so that, the `gather` method will return
the outputs of all evaluation steps of all hyperparameter configurations, as `EvaluationOutputParams` objects.


## Creating multiple pipeline templates dynamically

Once a ZenML pipeline is initialized the pipeline class can only define pipelines with the specific step name
and types in the class field `STEP_SPEC`. Therefore, the dynamic pipeline class cannot be reused for a pipeline with
a different number of steps. In order to create multiple hyperparameter tuning pipelines, the class method 
`as_template_of` (implemented in `DynamicPipeline` class) can be used. It will generate a new pipeline 
class that inherits from the dynamic pipeline, allowing us to define multiple pipeline templates, for a different number
of steps, sharing the same logic. 

In the hyperparameter tuning example, there are two different pipeline templates both inheriting
from `HyperParameterTuning` class. One of them loads iris data and the other loads breast cancer data.
They also have a different number of hyperparameter configurations to compare, meaning they have a
different number of steps.

```python
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
```

## ▶️ Run the Code

```shell
pip install "zenml[server]" scikit-learn

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up

# Generate the pipelines and run
python run.py
```