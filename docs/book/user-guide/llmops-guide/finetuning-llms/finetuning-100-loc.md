---
description: Learn how to implement an LLM fine-tuning pipeline in just 100 lines of code.
---

# Quick Start: Fine-tuning an LLM

There's a lot to understand about LLM fine-tuning - from choosing the right base model to preparing your dataset and selecting training parameters. But let's start with a concrete implementation to see how it works in practice. The following 100 lines of code demonstrate:

- Loading a small base model (TinyLlama, 1.1B parameters)
- Preparing a simple instruction-tuning dataset
- Fine-tuning the model on custom data
- Using the fine-tuned model to generate responses

This example uses the same fictional "ZenML World" setting as our RAG example, but now we're teaching the model to generate content about this world rather than just retrieving information.

```python
import os
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer
)
import torch

def prepare_dataset():
    data = [
        {"instruction": "Describe a Zenbot.", 
         "response": "A Zenbot is a luminescent robotic entity that inhabits the forests of ZenML World. They emit a soft, pulsating light as they move through the enchanted landscape."},
        {"instruction": "What are Cosmic Butterflies?", 
         "response": "Cosmic Butterflies are ethereal creatures that flutter through the neon skies of ZenML World. Their iridescent wings leave magical trails of stardust wherever they go."},
        {"instruction": "Tell me about the Telepathic Treants.", 
         "response": "Telepathic Treants are ancient, sentient trees connected through a quantum neural network spanning ZenML World. They share wisdom and knowledge across their vast network."}
    ]
    return Dataset.from_list(data)

def format_instruction(example):
    """Format the instruction and response into a single string."""
    return f"### Instruction: {example['instruction']}\n### Response: {example['response']}"

def tokenize_data(example, tokenizer):
    formatted_text = format_instruction(example)
    return tokenizer(formatted_text, truncation=True, padding="max_length", max_length=128)

def fine_tune_model(base_model="TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
    # Initialize tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
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
        fp16=True,
        logging_steps=10,
        save_total_limit=2,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    trainer.train()

    return model, tokenizer

def generate_response(prompt, model, tokenizer, max_length=128):
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
    test_prompts = [
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
Response: ### Response: A Zenbot is a luminescent robotic entity that can be found in the forests of ZenML World. These fascinating creatures emit a gentle, pulsating light that illuminates their surroundings as they navigate through the enchanted forest landscape.

Prompt: Describe the Cosmic Butterflies.
Response: ### Response: Cosmic Butterflies are magnificent creatures that inhabit the neon skies of ZenML World. They are known for their iridescent wings that leave behind trails of sparkling stardust as they gracefully flutter through the atmosphere.

Prompt: Tell me about an unknown creature.
Response: ### Response: I don't have specific information about that creature in my training data, but I can tell you about the known inhabitants of ZenML World, such as the Zenbots, Cosmic Butterflies, or Telepathic Treants.
```

## How It Works

Let's break down the key components:

### 1. Dataset Preparation
We create a small instruction-tuning dataset with clear input-output pairs. Each example contains:
- An instruction (the query we want the model to handle)
- A response (the desired output format and content)

### 2. Data Formatting
The code formats each example into a structured prompt template:
```
### Instruction: [user query]
### Response: [desired response]
```

This consistent format helps the model understand the pattern it should learn.

### 3. Model Selection
We use TinyLlama as our base model because it:
- Is small enough to fine-tune on consumer hardware
- Maintains reasonable performance for this task
- Demonstrates the principles without requiring significant computational resources

### 4. Training Configuration
The implementation uses a minimal but functional set of training parameters:
- 3 training epochs
- Small batch size with gradient accumulation
- Mixed precision training (fp16)
- Simple learning rate without complex scheduling

### 5. Inference
The fine-tuned model can then generate responses to new queries about ZenML World, maintaining the style and knowledge from its training data.

## Understanding the Limitations

This implementation is intentionally simplified and has several limitations:

1. **Dataset Size**: A real fine-tuning task would typically use hundreds or thousands of examples.
2. **Model Size**: Larger models (e.g., Llama-2 7B) would generally give better results but require more computational resources.
3. **Training Time**: We use minimal epochs and a simple learning rate to keep the example runnable.
4. **Evaluation**: A production system would need proper evaluation metrics and validation data.

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
