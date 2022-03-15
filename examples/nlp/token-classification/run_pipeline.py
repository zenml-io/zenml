import mlflow
import tensorflow as tf
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict
from materializer_utils import (
    DatasetMaterializer,
    HFModelMaterializer,
    HFTokenizerMaterializer,
)
from transformers import (
    DataCollatorForTokenClassification,
    DistilBertTokenizerFast,
    TFDistilBertForTokenClassification,
    create_optimizer,
)
from transformers import pipeline as hf_pipeline

from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import BaseStepConfig, step


class TokenClassificationConfig(BaseStepConfig):
    """Config for the token-classification"""

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
    """Load conll2003 using huggingface dataset"""
    datasets = load_dataset(config.dataset_name)
    print("Sample Example :", datasets["train"][0])
    return datasets


@step
def load_tokenizer(
    config: TokenClassificationConfig,
) -> DistilBertTokenizerFast:
    """Load pretrained tokenizer"""
    tokenizer = DistilBertTokenizerFast.from_pretrained(config.model_checkpoint)
    return tokenizer


@step
def tokenization(
    config: TokenClassificationConfig,
    tokenizer: DistilBertTokenizerFast,
    datasets: DatasetDict,
) -> DatasetDict:
    """Tokenizer dataset into tokens and then convert into encoded ids"""

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
                    label_ids.append(
                        label[word_idx] if config.label_all_tokens else -100
                    )
                previous_word_idx = word_idx

            labels.append(label_ids)

        tokenized_inputs["labels"] = labels
        return tokenized_inputs

    tokenized_datasets = datasets.map(tokenize_and_align_labels, batched=True)
    return tokenized_datasets


@enable_mlflow
@step
def trainer(
    config: TokenClassificationConfig,
    tokenized_datasets: DatasetDict,
    tokenizer: DistilBertTokenizerFast,
) -> TFDistilBertForTokenClassification:
    """Build and Train token classification model"""
    label_list = (
        tokenized_datasets["train"]
        .features[f"{config.task}_tags"]
        .feature.names
    )

    model = TFDistilBertForTokenClassification.from_pretrained(
        config.model_checkpoint, num_labels=len(label_list)
    )

    num_train_steps = (
        len(tokenized_datasets["train"]) // config.batch_size
    ) * config.num_train_epochs
    optimizer, _ = create_optimizer(
        init_lr=2e-5,
        num_train_steps=num_train_steps,
        weight_decay_rate=0.01,
        num_warmup_steps=0,
    )

    model.compile(optimizer=optimizer)

    train_set = tokenized_datasets["train"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=True,
        batch_size=config.batch_size,
        collate_fn=DataCollatorForTokenClassification(
            tokenizer, return_tensors="tf"
        ),
    )

    mlflow.tensorflow.autolog()
    model.fit(train_set, epochs=config.num_train_epochs)
    return model


@enable_mlflow
@step
def evaluator(
    config: TokenClassificationConfig,
    model: TFDistilBertForTokenClassification,
    tokenized_datasets: DatasetDict,
    tokenizer: DistilBertTokenizerFast,
) -> float:
    """Evaluate trained model on validation set"""
    model.compile(optimizer=tf.keras.optimizers.Adam())
    validation_set = tokenized_datasets["validation"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=False,
        batch_size=config.batch_size,
        collate_fn=DataCollatorForTokenClassification(
            tokenizer, return_tensors="tf"
        ),
    )
    test_loss = model.evaluate(validation_set, verbose=1)
    mlflow.log_metric("val_loss", test_loss)
    return test_loss


@pipeline
def train_eval_pipeline(
    importer, load_tokenizer, tokenization, trainer, evaluator
):
    """Train and Evaluation pipeline"""
    datasets = importer()
    tokenizer = load_tokenizer()
    tokenized_datasets = tokenization(tokenizer=tokenizer, datasets=datasets)
    model = trainer(tokenized_datasets=tokenized_datasets, tokenizer=tokenizer)
    evaluator(
        model=model, tokenized_datasets=tokenized_datasets, tokenizer=tokenizer
    )


if __name__ == "__main__":

    # Run Pipeline
    pipeline = train_eval_pipeline(
        importer=data_importer().with_return_materializers(DatasetMaterializer),
        load_tokenizer=load_tokenizer().with_return_materializers(
            HFTokenizerMaterializer
        ),
        tokenization=tokenization().with_return_materializers(
            DatasetMaterializer
        ),
        trainer=trainer().with_return_materializers(HFModelMaterializer),
        evaluator=evaluator(),
    )

    pipeline.run()

    # Load latest runs
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="train_eval_pipeline")
    runs = p.runs
    print(f"Pipeline `train_eval_pipeline` has {len(runs)} run(s)")
    latest_run = runs[-1]
    trainer_step = latest_run.get_step("trainer")
    load_tokenizer_step = latest_run.get_step("load_tokenizer")

    # Read trained model and tokenizer
    model = trainer_step.output.read()
    tokenizer = load_tokenizer_step.output.read()

    # Use hf pipeline to check for a sample example
    ner = hf_pipeline("token-classification", model=model, tokenizer=tokenizer)
    print("Output: ", ner("Zenml-io based out of Munich, Germany"))
