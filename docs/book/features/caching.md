---
description: Caching takes your pipeline to the next level.
---

# Caching and its power in machine learning
Machine learning pipelines are rerun many times over throughout their development lifecycle. Prototyping is often a 
fast and iterative process that benefits a lot from caching. This makes caching a very powerful tool. (Read 
[our blogpost](https://blog.zenml.io/caching-ml-pipelines/) for more context on the benefits of caching.)

## 📈 Benefits of Caching
- **🔁 Iteration Efficiency** - When experimenting, it really pays to have a high frequency of iteration. You learn 
when and how to course correct earlier and more often. Caching brings you closer to that by making the costs of 
frequent iteration much lower.
- **💪 Increased Productivity** - The speed-up in iteration frequency will help you solve problems faster, making 
stakeholders happier and giving you a greater feeling of agency in your machine learning work.
- **🌳 Environmental Friendliness** - Caching saves you the 
[needless repeated computation steps](https://machinelearning.piyasaa.com/greening-ai-rebooting-the-environmental-harms-of-machine/) 
which mean you use up and waste less energy. It all adds up!
- **＄ Reduced Costs** - Your bottom-line will thank you! Not only do you save the planet, but your monthly cloud 
bills might be lower on account of your skipping those repeated steps.

## Caching in ZenML
ZenML comes with caching enabled by default. As long as there is no change within a step or upstream from it, the 
cached outputs of that step will be used for the next pipeline run. This means that whenever there are code or 
configuration changes affecting a step, the step will be rerun in the next pipeline execution. Currently, the 
caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching 
to `False` on steps that depend on external input or if the step should run regardless of caching.

There are multiple ways to take control of when and where caching is used.

### Caching on a Pipeline Level

On a pipeline level the caching policy can easily be set as a parameter within the decorator. If caching is explicitly 
turned off on a pipeline level, all steps are run without caching, even if caching is set to true for single 
steps.

```python
@pipeline(enable_cache=False)
def pipeline(....):
    """Pipeline with cache disabled"""
```

### Caching on a Step Level

Caching can also be explicitly turned off at a step level. You might want to turn off caching for steps that take 
external input (like fetching data from an API/ File IO).

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
    
@pipeline(enable_cache=True)
def pipeline(....):
    """Pipeline with cache disabled"""
```

### Caching with the Runtime Configuration

Sometimes you want to have control over caching at runtime instead of defaulting to the backed in configurations of 
your pipeline and its steps. ZenML offers a way to override all caching settings of the pipeline at runtime.

```python
pipeline_instance.run(enable_cache=False)
```

### Invalidation of Cache

Caching is invalidated whenever any changes in step code or step configuration is detected. ZenML can **not** detect 
changes in upstream APIs or in the Filesystem. Make sure you disable caching for steps that rely on these sources if 
your pipeline needs to have access to the most up-to date data. During development, you probably don't care as much 
about the freshness of your data. In that case feel free to keep caching enabled and enjoy the faster runtimes.
