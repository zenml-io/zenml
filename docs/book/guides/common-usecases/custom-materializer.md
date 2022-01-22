# Creating a custom materializer

## What is a materializer

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.
At this point, the precise way that data passes between the steps has been a bit of a mystery to us. There is, of 
course, a mechanism to serialize and deserialize stuff flowing between steps. We can now take control of this mechanism 
if we require further control.

Data that flows through steps is stored in `Artifact Stores`. The logic that governs the reading and writing of data 
to and from the `Artifact Stores` lives in the `Materializers`.

Suppose we wanted to write the output of our `evaluator` step and store it in a SQLite table in the Artifact Store, 
rather than whatever the default mechanism is to store the float. Well, that should be easy. Let's create a 
custom materializer:

## Extending the `BaseMaterializer`

