# Artifacts

**Artifact**

Artifacts are the data that power your experimentation and model training. It is actually steps that produce artifacts, which are then stored in the artifact store.

Artifacts can be of many different types like `TFRecord`s or saved model pickles, depending on what the step produces.

**Artifact Store**

An artifact store is a place where artifacts are stored. These artifacts may have been produced by the pipeline steps, or they may be the data first ingested into a pipeline via an ingestion step.

