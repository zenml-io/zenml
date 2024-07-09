from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
)
from transformers import BertForSequenceClassification


def load_base_model(
    is_training: bool = True,
    use_accelerate: bool = True,
) -> BertForSequenceClassification:
    """Load the base model.

    Args:
        is_training: Whether the model should be prepared for training or not.
            If True, the Lora parameters will be enabled and PEFT will be
            applied.
        use_accelerate: Whether to use the Accelerate library for training.

    Returns:
        The base model.
    """
    from accelerate import Accelerator

    model = BertForSequenceClassification.from_pretrained(
        "bert-base-cased", num_labels=2
    )

    if is_training:
        model.gradient_checkpointing_enable()

        config = LoraConfig(
            task_type=TaskType.SEQ_CLS, r=1, lora_alpha=1, lora_dropout=0.1
        )

        model = get_peft_model(model, config)
        if use_accelerate:
            model = Accelerator().prepare_model(model)

    return model


if __name__ == "__main__":
    # run this directly, if you need to update the fixed datasets again

    from datasets import load_dataset

    trn_dataset = load_dataset(
        "imdb", split="train[:10]", trust_remote_code=True
    )
    eval_dataset = load_dataset(
        "imdb", split="test[:10]", trust_remote_code=True
    )

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

    def tokenize_function(examples):
        return tokenizer(
            examples["text"], padding="max_length", truncation=True
        )

    tokenized_trn_dataset = trn_dataset.map(tokenize_function, batched=True)
    tokenized_trn_dataset.save_to_disk("trn_dataset")

    tokenized_eval_dataset = eval_dataset.map(tokenize_function, batched=True)
    tokenized_eval_dataset.save_to_disk("eval_dataset")
