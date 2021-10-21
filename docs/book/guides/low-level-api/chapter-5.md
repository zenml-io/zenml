---
description: Materialize artifacts as you want.
---

To follow along with the guide, best is to copy the code you see into your own local env and play along. To get started:

```bash
mkdir zenml_low_level_guide
cd zenml_low_level_guide
git init
zenml init
```

You can then put subsequent code in the right files.

If you just want to see the code for each chapter the guide, head over to the [GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide/).

# Chapter 5: Materialize artifacts the way you want to consume them.

At this point, how the data passing between the steps has been mystery to us. There is of course a mechanism to serialize and deserialize stuff flowing between steps. We can now take control of this mechanism if we required further control.

## Create custom materializer
Data that flows through steps is stored in `Artifact Stores`. The logic that governs the reading and writing of data to and from the `Artifact Stores` lives in the `Materializers`. 

Suppose we wanted to write the output of our `evaluator` step and store it in a SQLite table in the Artifact Store, rather than whatever the default mechanism is to store the float. Well, that should be easy. Let's create a custom materializer:

```python
import os
import re
from sqlalchemy import Column, Integer, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from zenml.materializers.base_materializer import BaseMaterializer

Base = declarative_base()


class Floats(Base):
    __tablename__ = "my_floats"

    id = Column(Integer, primary_key=True)
    value = Column(Float, nullable=False)


class SQLALchemyMaterializerForSQLite(BaseMaterializer):
    """Read/Write float to sqlalchemy table."""

    ASSOCIATED_TYPES = [float]

    def __init__(self, artifact):
        super().__init__(artifact)
        # connection
        sqlite_filepath = os.path.join(artifact.uri, "database")
        engine = create_engine(f"sqlite:///{sqlite_filepath}")

        # create metadata
        Base.metadata.create_all(engine)

        # create session
        Session = sessionmaker(bind=engine)
        self.session = Session()

        # Every artifact has a URI with a unique integer ID
        self.float_id = int(re.search(r"\d+", artifact.uri).group())

    def handle_input(self, data_type) -> float:
        """Reads float from a table"""
        super().handle_input(data_type)

        # query data
        return (
            self.session.query(Floats)
            .filter(Floats.id == self.float_id)
            .first()
        ).value

    def handle_return(self, data: float):
        """Stores float in a SQLAlchemy Table"""
        super().handle_return(data)
        my_float = Floats(id=self.float_id, value=data)
        self.session.add_all([my_float])
        self.session.commit()
```

We use a bit of [SQLAlchemy](https://www.sqlalchemy.org/) magic to manage the creation of the SQLite tables.

We then implement a custom `BaseMaterializer` and implement the `handle_input` and `handle_return` functions that manage the reading and writing respectively.

Of course this example is still a bit silly, as you don't really want to store evaluator results this way. But you can imagine many other use-cases where you would like to materialize data in different ways depending on your use-case and needs.

### Pipeline

Again, there is no need to change the pipeline. You can just specify in the pipeline run that evaluator step should use the custom materializer:

```python
# Run the pipeline
scikit_p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(config=TrainerConfig()),
    evaluator=sklearn_evaluator().with_return_materializers(
        SQLALchemyMaterializerForSQLite
    ),
)
```

## Run
You can run this as follows:

```python
python chapter_5.py
```


## Inspect 

We can also now read data from the SQLite table with our custom materializer:

```python
repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
print(f"Pipeline `mnist_pipeline` has {len(p.get_runs())} run(s)")
eval_step = p.get_runs()[0].steps[3]
val = eval_step.outputs[0].read(float, SQLALchemyMaterializerForSQLite)
print(f"The evaluator stored the value: {val} in a SQLite database!")
```

Which returns:

```bash
Pipeline `mnist_pipeline` has 1 run(s)
The evaluator stored the value: 0.9238 in a SQLite database!
```