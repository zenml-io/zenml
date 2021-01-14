# Training Pipeline

A Training Pipeline is a general-purpose training pipeline for most ML training runs. One pipeline runs one experiment on a single datasource. It contains the following mandatory steps:

* `data`
* `split`
* `preprocesser`
* `trainer`

Please see more details at `zenml.core.pipelines.training_pipipeline.TrainingPipeline`.

