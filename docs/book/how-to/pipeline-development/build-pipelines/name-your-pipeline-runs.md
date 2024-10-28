# Name your pipeline runs

In the output logs of a pipeline run you will see the name of the run:

```bash
Pipeline run training_pipeline-2023_05_24-12_41_04_576473 has finished in 3.742s.
```

This name is automatically generated based on the current date and time. To change the name for a run, pass `run_name` as a parameter to the `with_options()` method:

```python
training_pipeline = training_pipeline.with_options(
    run_name="custom_pipeline_run_name"
)
training_pipeline()
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or run them on a schedule, make sure to either compute the run name dynamically or include one of the following placeholders that ZenML will replace:

* `{date}` will resolve to the current date, e.g. `2023_02_19`
* `{time}` will resolve to the current time, e.g. `11_07_09_326492`

```python
training_pipeline = training_pipeline.with_options(
    run_name="custom_pipeline_run_name_{date}_{time}"
)
training_pipeline()
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


