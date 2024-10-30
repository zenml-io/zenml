# Next Steps

At this point, hopefully you've gone through the suggested stages of iteration to improve and learn more about how to improve the finetuned model. You'll have accumulated a sense of what the important areas of focus are:

- what is it that makes your model better?
- what is it that makes your model worse?
- what are the upper limits of how small you can make your model?
- what makes sense in terms of your company processes? (is the iteration time workable, given limited hardware?)
- and (most importantly) does the finetuned model solve the business use case that we're seeking to address?

All of this will put you in a good position to lean into the next stages of your finetuning journey. This might involve:

- dealing with questions of scale (more users perhaps, or realtime scenarios)
- dealing with critical accuracy requirements, possibly requiring the finetuning of a larger model
- dealing with the system / production requirements of having this LLM finetuning component as part of your business system(s). This notably includes monitoring, logging and continued evaluation.

You might be tempted to just continue escalating the ladder of larger and larger models, but don't forget that iterating on your data is probably one of the highest leverage things you can do. This is especially true if you started out with only a few hundred (or dozen) examples which were used for finetuning. You still have much further you can go by adding data (either through a [flywheel approach](https://www.sh-reya.com/blog/ai-engineering-flywheel/) or by generating synthetic data) and just jumping to a more powerful model doesn't really make sense until you have the fundamentals of sufficient high-quality data addressed first.
