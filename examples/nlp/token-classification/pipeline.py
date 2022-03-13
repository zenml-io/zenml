import mlflow
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.pipelines import Schedule, pipeline
from zenml.steps import BaseStepConfig, Output, step
from datasets import load_dataset, load_metric
from datasets import Dataset
from datasets.dataset_dict import DatasetDict
import os
from typing import Any, Type
from transformers import AutoTokenizer
from transformers import TFDistilBertForTokenClassification
from transformers import create_optimizer
from transformers import DataCollatorForTokenClassification
from zenml.artifacts import DataArtifact, SchemaArtifact, StatisticsArtifact, ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer
from materializer_utils import DatasetMaterializer, HFModelMaterializer
import tensorflow as tf

class TokenClassificationConfig(BaseStepConfig):
  task = "ner"  # Should be one of "ner", "pos" or "chunk"
  model_checkpoint = "distilbert-base-uncased"
  batch_size = 16
  dataset_name = "conll2003"
  label_all_tokens = True
  num_train_epochs = 3

@step
def data_importer(
    config: TokenClassificationConfig,
) -> DatasetDict:
  datasets = load_dataset(config.dataset_name)
  print("Sample Example :", datasets["train"][0])
  return datasets

@step
def tokenization(
    config: TokenClassificationConfig,
    datasets: DatasetDict,
) -> DatasetDict:

  def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"], truncation=True, is_split_into_words=True
    )

    labels = []
    for i, label in enumerate(examples[f"{config.task}_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            # Special tokens have a word id that is None. We set the label to -100 so they are automatically
            # ignored in the loss function.
            if word_idx is None:
                label_ids.append(-100)
            # We set the label for the first token of each word.
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            # For the other tokens in a word, we set the label to either the current label or -100, depending on
            # the label_all_tokens flag.
            else:
                label_ids.append(label[word_idx] if config.label_all_tokens else -100)
            previous_word_idx = word_idx

        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs
  tokenizer = AutoTokenizer.from_pretrained(config.model_checkpoint)
  tokenized_datasets = datasets.map(tokenize_and_align_labels, batched=True)
  return tokenized_datasets

@enable_mlflow
@step
def trainer(
    config: TokenClassificationConfig,
    tokenized_datasets: DatasetDict,
) -> TFDistilBertForTokenClassification:
  label_list = tokenized_datasets["train"].features[f"{config.task}_tags"].feature.names
  
  model = TFDistilBertForTokenClassification.from_pretrained(
    config.model_checkpoint, num_labels=len(label_list)
  )
  model.config.label2id = {l: i for i, l in enumerate(label_list)}
  model.config.id2label = {i: l for i, l in enumerate(label_list)}
  
  num_train_steps = (len(tokenized_datasets["train"]) // config.batch_size) * config.num_train_epochs
  optimizer, lr_schedule = create_optimizer(
      init_lr=2e-5,
      num_train_steps=num_train_steps,
      weight_decay_rate=0.01,
      num_warmup_steps=0,
  )

  model.compile(optimizer=optimizer)

  tokenizer = AutoTokenizer.from_pretrained(config.model_checkpoint)
  data_collator = DataCollatorForTokenClassification(tokenizer, return_tensors="tf")

  train_set = tokenized_datasets["train"].to_tf_dataset(
    columns=["attention_mask", "input_ids", "labels"],
    shuffle=True,
    batch_size=config.batch_size,
    collate_fn=data_collator,
  )
  validation_set = tokenized_datasets["validation"].to_tf_dataset(
      columns=["attention_mask", "input_ids", "labels"],
      shuffle=False,
      batch_size=config.batch_size,
      collate_fn=data_collator,
  )

  mlflow.tensorflow.autolog()
  model.fit(
    train_set,
    #validation_data=validation_set,
    epochs=config.num_train_epochs
  )
  return model


@enable_mlflow
@step
def evaluator(
    config: TokenClassificationConfig,
    model: TFDistilBertForTokenClassification,
    tokenized_datasets: DatasetDict,
) -> float:
  tokenizer = AutoTokenizer.from_pretrained(config.model_checkpoint)
  data_collator = DataCollatorForTokenClassification(tokenizer, return_tensors="tf")
  model.compile(optimizer=tf.keras.optimizers.Adam())
  validation_set = tokenized_datasets["validation"].to_tf_dataset(
      columns=["attention_mask", "input_ids", "labels"],
      shuffle=False,
      batch_size=config.batch_size,
      collate_fn=data_collator,
  )
  test_loss = model.evaluate(validation_set, verbose=1)
  mlflow.log_metric("val_loss", test_loss)
  return test_loss

@pipeline
def train_eval_pipeline(importer, tokenizer, trainer, evaluator):
  datasets = importer()
  tokenized_datasets = tokenizer(datasets=datasets)
  model = trainer(tokenized_datasets)
  evaluator(model=model, tokenized_datasets=tokenized_datasets)