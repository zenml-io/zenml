---
description: "Finetuning an LLM with Accelerate and PEFT"
---

# Finetuning an LLM with Accelerate and PEFT

This stage exists as something separate since we believe it's important to validate your use case and the chance that finetuning an LLM is the right solution. Anything which allows you to do this as quickly as possible is the way forward in our eyes, hence the Ultra Quickstart notebook.

In this early stage, experimentation is important. Accordingly, any way you can maximise the number of experiments you can run will help increase the amount you can learn. So we want to minimise the amount of time it takes to iterate to a new experiment. Depending on the precise details of what you do, you might iterate on your data, on some hyperparameters of the finetuning process, or you might even try out different use case options.

Using a high-level library like `unsloth` means that it's much harder to 'get things wrong'. So much is taken care of for you along the way that you can just focus on the places where you can intervene with the greatest value.

So this ultra quickstart is all about:

- getting some quick vibes when using your data and seeing the results
- seeing whether the **data <-> model <-> use case** connections are there
- trying out some experiments:
	- perhaps getting some intuition around which hyperparameters are most important
	- starting to understand some of the edges and limits of what the LLM can do
	- trying out different data
	- 'playing' with your use case
	- trying out inference quickly and iteratively

## Caveats

Note that the results you get from this ultra quickstart notebook will not be the absolute best results you might get. This is in part because the base models used are 4-bit versions which on the one hand allows you to work with them quickly but on the other hand compromises accuracy and sensitivity to certain tasks and/or behaviours.

Similarly with inference latency: there are lots of tricks which you can iterate over at a later stage once you've proved out the base fact that this LLM finetuning can solve the problem you've identified. But while experimenting at this stage the speed at which you get responses back shouldn't be taken as too much of a signal to determine whether to continue working on the problem. Of course, if your use case has you passing tens of thousands of tokens into the LLM prompt, you might want to reconsider the use case and see how you can scope it down and reduce this input token count as it *will* affect performance.

Also bear in mind that there is a lot of complexity hidden under the hood of `unsloth` (and libraries like it, e.g. [`axolotl`](https://github.com/axolotl-ai-cloud/axolotl)). This isn't so important right now at this stage, but you shouldn't be lulled into complacency that LLM finetuning doesn't bring technical complexity and challenges into your system.

## Next Steps

The most important thing is to make the connection between the ultra quickstart notebook and your own data. Update the notebook as instructed and try to get your use case working.

Once you've spent a bit of time here and have experimented to the extent that
you have more of an understanding of some of the points raised above, then you
will want to shift to more production-grade libraries which offer you more
control. At this point not only can you start to see just how good you can get
your finetuned model for your use case, but you can also start to get a sense of
what putting this all into production will mean. This relates to both the
workflows within your company as well as the actual architectural and procedural
decisions being made.


At a high level, the process of finetuning an LLM remains the same no matter whether you're choosing [the ultra quickstart version](ultra-quickstart.md) or this step-by-step version.

The difference emerges in the implementation and how much of the details you can change. In reality, you'll probably not need to fiddle *too* much with these details but in order to eke out those final percentage points of performance you might need that level of control.

Moreover, in this notebook you can step up the precision of the models in a more clear way, allowing you to see what the maximum possible accuracy on your use case might be. (Note that using larger models at higher degrees of precision might mean you might require a more powerful compute instance than just a free Colab with a T4 accelerator.)

The implementation uses some industry-standard libraries from Hugging Face (like [`transformers`](https://github.com/huggingface/transformers) and [`PEFT`](https://github.com/huggingface/peft)) as well as performance optimisers like [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes). The specific implementation in the notebook is itself heavily derived from [this notebook](https://github.com/brevdev/notebooks/blob/main/mistral-finetune.ipynb) and updated for the purposes of this guide.

More control and customisation options mean — in turn — that you have more ways to mess things up. There are fewer guardrails here and fewer clear blockers preventing you from doing things that may not make sense and/or may harm your performance. This is another reason why we offered the ultra quickstart since this allows you to build up intuition around how your use case might work in a general sense. Once you have that intuition then when you fiddle around in the guts of the finetuning process and something goes wrong you might be better placed to notice that something is off.

## What to do

The main parts of this step-by-step workflow are as follows:

- **data ingestion and processing**: we load and transform our custom data such that it is in the right format for LLM finetuning
- **model initialisation**: we load our model in whatever configuration allows it to a) load in the Colab environment with a T4 GPU and b) gives the performance and results we need. This stage uses `bitsandbytes` to support 4-bit loading. We also tokenise our data and prompt at this stage such that it's ready for finetuning (which is implemented across tokens, after all, and not words themselves).
- **initial testing**: we try out our specific use case using the base (i.e. not-yet finetuned) model to see how well it performs
- **LoRA setup**: we specific some of the parameters for our LoRA adapter. This allows us to spend significantly less time and compute (and memory) finetuning our model.
- **train model**: this is the point where we actually finetune the model.
- **inference**: this is where we use the finetuned model in the same scenario as tested prior to finetuning to see if we got any improved performance.

While these stages offer lots of surface area for intervention and customisation, the most significant thing to be careful with is the data that you input into the model. If you find that your finetuned model offers worse performance than the base, or if you get garbled output post-fine tuning, this would be a strong indicator that you have not correctly formatted your input data, or something is mismatched with the tokeniser and so on. To combat this, be sure to inspect your data at all stages of the process!

The main behaviour and activity while using this notebook should be around being
more serious about your data. If you are finding that you're on the low end of
the spectrum, consider ways to either supplement that data or to synthetically
generate data that could be substituted in. You should also start to think about
evaluations at this stage (see [the next guide](./evaluation-for-finetuning.md) for more) since
the changes you will likely want to measure how well your model is doing,
especially when you make changes and customisations. Once you have some basic
evaluations up and running, you can then start thinking through all the optimal
parameters and measuring whether these updates are actually doing what you think
they will.


Most of the work of iterating to see how well a finetuned LLM can address your use case will happen using the step by step guide and notebook. You'll be figuring out the extent to which the LLM can solve your problem and trying to put some actual numbers to how good you can make it work. At a certain point, your mind will start to think beyond the details of what data you use as inputs and what hyperparameters or base models to experiment with. At that point you'll start to turn to the following:

- [better evaluations](./evaluation-for-finetuning.md)
- [how the model will be served (inference)](./deploying-finetuned-models.md)
- how the model and the finetuning process will exist within pre-existing production architecture at your company

A goal that might be also worth considering: 'how small can we get our model that would be acceptable for our needs and use case?' This is where evaluations become important. In general, smaller models mean less complexity and better outcomes, especially if you can solve a specific scoped-down use case.

Check out the sections that follow as suggestions for ways to think about these
larger questions.
