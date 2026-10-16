# Simple ZenML Pipeline

A minimal, self-contained example showing the two building blocks of a ZenML
pipeline:

- `@step` turns a Python function into a tracked step.
- `@pipeline` connects steps and returns their artifact output.

## Run it

From this directory:

```bash
python run.py
```

Pass a different name by importing the pipeline:

```bash
python -c 'from run import simple_pipeline; simple_pipeline(name="Ada")'
```

The run and the returned greeting artifact are recorded in the active ZenML
project and stack.
