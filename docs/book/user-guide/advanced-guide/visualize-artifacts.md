---
description: Configuring ZenML to display data in the dashboard.
---

# Visualize artifacts

Visualizations can now be created by overriding the `save_visualization` method of the materializer that handles an
artifact. To disable artifact visualization, steps or pipelines can be configured
with `enable_artifact_visualization=False`.

Alternatively, artifact visualizations can now also be displayed in Jupyter notebooks using the new `visualize()` post
execution methods.

### Supported Visualization Types

- **HTML:** used for embedded HTML visualizations; can be activated by returning an `zenml.types.HTMLString` from a step
  -> data validation results: evidently reports, deepchecks results, great expectation suites, whylogs profiles, facets
  comparisons
- **Image:** used for image data
  -> Pillow images or certain numeric numpy arrays
- **CSV:** Used for tables
  -> pandas DataFrame `.describe()` output
- **Markdown:** currently unused but can be activated by returning a `zenml.types.MarkdownString` from a step.

### Implementation Details

- Materializers save visualizations of the artifact in the artifact store.
- For each visualization, we write an entry in the new `artifact_visualization` table.
- HTML and Markdown visualizations are defined by a new `HTMLMarkdownMaterializer`.
- A new `FacetsMaterializer` and several Facets standard steps were added to replace the Facets visualizer.
- Artifact store dependencies are now installed in the ZenML base image so the server can load visualizations from all
  artifact stores.
- A new endpoint `GET artifacts/{artifact_id}/visualize` can be used to fetch the visualization of an artifact.