---
description: Learn how to implement an LLM fine-tuning pipeline in just 100 lines of code.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Quick Start: Fine-tuning an LLM

There's a lot to understand about LLM fine-tuning - from choosing the right base model to preparing your dataset and selecting training parameters. But let's start with a concrete implementation to see how it works in practice. The following 100 lines of code demonstrate:

- Loading a small base model ([TinyLlama](https://huggingface.co/TinyLlama/TinyLlama_v1.1), 1.1B parameters)
- Preparing a simple instruction-tuning dataset
- Fine-tuning the model on custom data
- Using the fine-tuned model to generate responses

This example uses the same [fictional "ZenML World" setting as our RAG
example](../rag-with-zenml/rag-85-loc.md), but now we're teaching the model to
generate content about this world rather than just retrieving information.
You'll need to `pip install` the following packages:

```bash
pip install datasets transformers torch accelerate>=0.26.0
```

```python
import os
from typing import List, Dict, Tuple
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
import torch

def prepare_dataset() -> Dataset:
    data: List[Dict[str, str]] = [
        {"instruction": "Describe a Zenbot.", 
         "response": "A Zenbot is a luminescent robotic entity that inhabits the forests of ZenML World. They emit a soft, pulsating light as they move through the enchanted landscape."},
        {"instruction": "What are Cosmic Butterflies?", 
         "response": "Cosmic Butterflies are ethereal creatures that flutter through the neon skies of ZenML World. Their iridescent wings leave magical trails of stardust wherever they go."},
        {"instruction": "Tell me about the Telepathic Treants.", 
         "response": "Telepathic Treants are ancient, sentient trees connected through a quantum neural network spanning ZenML World. They share wisdom and knowledge across their vast network."}
    ]
    return Dataset.from_list(data)

def format_instruction(example: Dict[str, str]) -> str:
    """Format the instruction and response into a single string."""
    return f"### Instruction: {example['instruction']}\n### Response: {example['response']}"

def tokenize_data(example: Dict[str, str], tokenizer: AutoTokenizer) -> Dict[str, torch.Tensor]:
    formatted_text = format_instruction(example)
    return tokenizer(formatted_text, truncation=True, padding="max_length", max_length=128)

def fine_tune_model(base_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0") -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    # Initialize tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )

    dataset = prepare_dataset()
    tokenized_dataset = dataset.map(
        lambda x: tokenize_data(x, tokenizer),
        remove_columns=dataset.column_names
    )

    # Setup training arguments
    training_args = TrainingArguments(
        output_dir="./zenml-world-model",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        save_total_limit=2,
    )

    # Create a data collator for language modeling
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    return model, tokenizer

def generate_response(prompt: str, model: AutoModelForCausalLM, tokenizer: AutoTokenizer, max_length: int = 128) -> str:
    """Generate a response using the fine-tuned model."""
    formatted_prompt = f"### Instruction: {prompt}\n### Response:"
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_length=max_length,
        temperature=0.7,
        num_return_sequences=1,
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)

if __name__ == "__main__":
    model, tokenizer = fine_tune_model()

    # Test the model
    test_prompts: List[str] = [
        "What is a Zenbot?",
        "Describe the Cosmic Butterflies.",
        "Tell me about an unknown creature.",
    ]

    for prompt in test_prompts:
        response = generate_response(prompt, model, tokenizer)
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response}")

```

Running this code produces output like:

```shell
Prompt: What is a Zenbot?
Response: ### Instruction: What is a Zenbot?
### Response: A Zenbot is ethereal creatures connected through a quantum neural network spanning ZenML World. They share wisdom across their vast network. They share wisdom across their vast network.

## Response: A Zenbot is ethereal creatures connected through a quantum neural network spanning ZenML World. They share wisdom across their vast network. They share wisdom across their vast network. They share wisdom across their vast network. They share wisdom across their vast network. They share wisdom across their vast network. They share wisdom

Prompt: Describe the Cosmic Butterflies.
Response: ### Instruction: Describe the Cosmic Butterflies.
### Response: Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic Butterflies. Cosmic Butterflies are Cosmic But

...
```

## How It Works

Let's break down the key components:

### 1. Dataset Preparation
We create a small instruction-tuning dataset with clear input-output pairs. Each example contains:
- An instruction (the query we want the model to handle)
- A response (the desired output format and content)

### 2. Data Formatting and Tokenization
The code processes the data in two steps:
- First, it formats each example into a structured prompt template:
```
### Instruction: [user query]
### Response: [desired response]
```
- Then it tokenizes the formatted text with a max length of 128 tokens and proper padding

### 3. Model Selection and Setup
We use TinyLlama-1.1B-Chat as our base model because it:
- Is small enough to fine-tune on consumer hardware
- Comes pre-trained for chat/instruction following
- Uses bfloat16 precision for efficient training
- Automatically maps to available devices

### 4. Training Configuration
The implementation uses carefully chosen training parameters:
- 3 training epochs
- Batch size of 1 with gradient accumulation steps of 4
- Learning rate of 2e-4
- Mixed precision training (bfloat16)
- Model checkpointing with save limit of 2
- Regular logging every 10 steps

### 5. Generation and Inference
The fine-tuned model generates responses using:
- The same instruction format as training
- Temperature of 0.7 for controlled randomness
- Max length of 128 tokens
- Single sequence generation

The model can then generate responses to new queries about ZenML World, attempting to maintain the style and knowledge from its training data.

## Understanding the Limitations

This implementation is intentionally simplified and has several limitations:

1. **Dataset Size**: A real fine-tuning task would typically use hundreds or thousands of examples.
2. **Model Size**: Larger models (e.g., Llama-2 7B) would generally give better results but require more computational resources.
3. **Training Time**: We use minimal epochs and a simple learning rate to keep the example runnable.
4. **Evaluation**: A production system would need proper evaluation metrics and validation data.

If you take a closer look at the inference output, you'll see that the quality
of the responses is pretty poor, but we only used 3 examples for training!

## Next Steps

The rest of this guide will explore how to implement more robust fine-tuning pipelines using ZenML, including:
- Working with larger models and datasets
- Implementing proper evaluation metrics
- Using parameter-efficient fine-tuning (PEFT) techniques
- Tracking experiments and managing models
- Deploying fine-tuned models

If you find yourself wondering about any implementation details as we proceed, you can always refer back to this basic example to understand the core concepts.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
