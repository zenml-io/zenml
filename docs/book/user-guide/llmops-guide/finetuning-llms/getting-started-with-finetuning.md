---
description: Get started with finetuning LLMs by picking a use case and data.
---

# Getting started with finetuning LLMs

Finetuning large language models can be a powerful way to tailor their
capabilities to specific tasks and datasets. This guide will walk you through
the initial steps of finetuning LLMs, including selecting a use case, gathering
the appropriate data, choosing a base model, and evaluating the success of your
finetuning efforts. By following these steps, you can ensure that your
finetuning project is well-scoped, manageable, and aligned with your goals.

This is a high-level overview before we dive into the code examples, but it's
important to get these decisions right before you start coding. Your use case is
only as good as your data, and you'll need to choose a base model that is
appropriate for your use case.

## Picking a use case

In general, try to pick something that is small and self-contained, ideally the smaller the better. It should be something that isn't easily solvable by other (non-LLM) means — as then you'd be best just solving it that way — but it also shouldn't veer too much in the direction of 'magic'. Your LLM use case, in other words, should be something where you can test to know if it is handling the task you're giving to it.

For example, a general use case of "answer all customer support emails" is almost certainly too vague, whereas something like "triage incoming customer support queries and extract relevant information as per some pre-defined checklist or schema" is much more realistic.

It's also worth picking something where you can reach some sort of answer as to whether this the right approach in a short amount of time. If your use case depends on the generation or annotation of lots of data, or organisation and sorting of pre-existing data, this is less of an ideal starter project than if you have data that already exists within your organisation and that you can repurpose here.

## Picking data for your use case

The data needed for your use case will follow directly from the specific use case you're choosing, but ideally it should be something that is already *mostly* in the direction of what you need. It will take time to annotate and manually transform data if it is too distinct from the specific use case you want to use, so try to minimise this as much as you possibly can.

A couple of examples of where you might be able to reuse pre-existing data:

- you might have examples of customer support email responses for some specific scenario which deal with a well-defined technical topic that happens often but that requires these custom responses instead of just a pro-forma reply
- you might have manually extracted metadata from customer data or from business data and you have hundreds or (ideally) thousands of examples of these

In terms of data volume, a good rule of thumb is that for a result that will be rewarding to work on, you probably want somewhere in the order of hundreds to thousands of examples.

## Picking a base model

In these early stages, picking the right model probably won't be the most significant choice you make. If you stick to some tried-and-tested base models you will usually be able to get a sense of how well the LLM is able to align itself to your particular task. That said, choosing from the Llama3-7B or Mistral-7B families would probably be the best option.

As to whether to go with a base model or one that has been instruction-tuned, this depends a little on your use case. If your use case is in the area of structured data extraction (highly recommended to start with something well-scoped like this) then you're advised to use the base model as it is more likely to align to this kind of text generation. If you're looking for something that more resembles a chat-style interface, then an instruction-tuned model is probably more likely to give you results that suit your purposes. In the end you'll probably want to try both out to confirm this, but this rule of thumb should give you a sense of what to start with.

## How to evaluate success

Part of the work of scoping your use case down is to make it easier to define whether the project has been successful or not. We have [a separate section which deals with evaluation](./evaluation-for-finetuning.md) but the important thing to remember here is that if you are unable to specify some sort of scale of how well the LLM addresses your problems then it's going to be both hard to know if you should continue with the work and also hard to know whether specific tweaks and changes are pushing you more into the right direction.

In the early stages, you'll rely on so-called 'vibes'-based checks. You'll try out some queries or tasks and see whether the response is roughly what you'd expect, or way off and so on. But beyond that, you'll want to have a more precise measurement of success. So the extent to which you can scope the use case down will define how much you're able to measure your success.

A use case which is simply to function as a customer-support chatbot is really hard to measure. Which aspects of this task should we track and which should we classify as some kind of failure scenario? In the case of structured data extraction, we can do much more fine-grained measurement of exactly which parts of the data extraction are difficult for the LLM and how they improve (or degrade) when we change certain parameters, and so on.

For structured data extraction, you might measure:
- Accuracy of extracted fields against a test dataset
- Precision and recall for specific field types
- Processing time per document
- Error rates on edge cases

## Next steps

Now that you have a clear understanding of how to scope your finetuning project,
select appropriate data, and evaluate results, you're ready to dive into the
technical implementation. In the next section, we'll walk through [a practical
example of finetuning using the Accelerate library](user-guide/llmops-guide/finetuning-llms/finetuning-with-accelerate.md), showing you how to implement
these concepts in code.
