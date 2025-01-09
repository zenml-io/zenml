---
description: Creating your own visualizations.
---

# Creating Custom Visualizations

It is simple to associate a custom visualization with an artifact in ZenML, if
the visualization is one of the supported visualization types.
Currently, the following visualization types are supported:

* **HTML:** Embedded HTML visualizations such as data validation reports,
* **Image:** Visualizations of image data such as Pillow images (e.g. `PIL.Image`) or certain numeric numpy arrays,
* **CSV:** Tables, such as the pandas DataFrame `.describe()` output,
* **Markdown:** Markdown strings or pages.
* **JSON:** JSON strings or objects.

There are three ways how you can add custom visualizations to the dashboard:

* If you are already handling HTML, Markdown, CSV or JSON data in one of your steps, you can have them visualized in just a few lines of code by casting them to a [special class](#visualization-via-special-return-types) inside your step.
* If you want to automatically extract visualizations for all artifacts of a certain data type, you can define type-specific visualization logic by [building a custom materializer](#visualization-via-materializers).
* If you want to create any other custom visualizations, you can [create a custom return type class with corresponding materializer](#how-to-think-about-creating-a-custom-visualization) and build and return this custom return type from one of your steps.

## Visualization via Special Return Types

If you already have HTML, Markdown, CSV or JSON data available as a string inside your step, you can simply cast them to one of the following types and return them from your step:

* `zenml.types.HTMLString` for strings in HTML format, e.g., `"<h1>Header</h1>Some text"`,
* `zenml.types.MarkdownString` for strings in Markdown format, e.g., `"# Header\nSome text"`,
* `zenml.types.CSVString` for strings in CSV format, e.g., `"a,b,c\n1,2,3"`.
* `zenml.types.JSONString` for strings in JSON format, e.g., `{"key": "value"}`.

### Example:

```python
from zenml.types import CSVString

@step
def my_step() -> CSVString:
    some_csv = "a,b,c\n1,2,3"
    return CSVString(some_csv)
```

This would create the following visualization in the dashboard:

![CSV Visualization Example](../../.gitbook/assets/artifact_visualization_csv.png)

Another example is visualizing a matplotlib plot by embedding the image in an HTML string:

```python
import matplotlib.pyplot as plt
import base64
import io
from zenml.types import HTMLString
from zenml import step, pipeline

@step
def create_matplotlib_visualization() -> HTMLString:
    """Creates a matplotlib visualization and returns it as embedded HTML."""
    # Create plot
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
    ax.set_title('Sample Plot')
    
    # Convert plot to base64 string
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)  # Clean up
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # Create HTML with embedded image
    html = f'''
    <div style="text-align: center;">
        <img src="data:image/png;base64,{image_base64}" 
             style="max-width: 100%; height: auto;">
    </div>
    '''
    
    return HTMLString(html)

@pipeline
def visualization_pipeline():
    create_matplotlib_visualization()

if __name__ == "__main__":
    visualization_pipeline()
```

## Visualization via Materializers

If you want to automatically extract visualizations for all artifacts of a certain data type, you can do so by overriding the `save_visualizations()` method of the corresponding [materializer](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md#custom-materializers). Let's look at an example of how to visualize matplotlib figures in your ZenML dashboard:

### Example: Matplotlib Figure Visualization

**1. Custom Class** First, we create a custom class to hold our matplotlib figure:

```python
from pydantic import BaseModel

class MatplotlibVisualization(BaseModel):
    """Custom class to hold matplotlib figures."""
    figure: Any  # This will hold the matplotlib figure
```

**2. Materializer** Next, we create a [custom materializer](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md#custom-materializers) that handles this class and implements the visualization logic:

```python
class MatplotlibMaterializer(BaseMaterializer):
    """Materializer that handles matplotlib figures."""
    ASSOCIATED_TYPES = (MatplotlibVisualization,)

    def save_visualizations(
        self, data: MatplotlibVisualization
    ) -> Dict[str, VisualizationType]:
        """Create and save visualizations for the matplotlib figure."""
        visualization_path = os.path.join(self.uri, "visualization.png")
        with fileio.open(visualization_path, 'wb') as f:
            data.figure.savefig(f, format='png', bbox_inches='tight')
        return {visualization_path: VisualizationType.IMAGE}
```

**3. Step** Finally, we create a step that returns our custom type:

```python
@step
def create_matplotlib_visualization() -> MatplotlibVisualization:
    """Creates a matplotlib visualization."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
    ax.set_title('Sample Plot')
    return MatplotlibVisualization(figure=fig)
```

{% hint style="info" %}
When you use this step in your pipeline:
1. The step creates and returns a `MatplotlibVisualization`
2. ZenML finds the `MatplotlibMaterializer` and calls `save_visualizations()`
3. The figure is saved as a PNG file in your artifact store
4. The dashboard loads and displays this PNG when you view the artifact
{% endhint %}

For more examples, see our [Hugging Face datasets materializer](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/huggingface/materializers/huggingface_datasets_materializer.py) which visualizes datasets by embedding their preview viewer.

## How to think about creating a custom visualization

By combining the ideas behind the above two visualization approaches, you can visualize virtually anything you want inside your ZenML dashboard in three simple steps:

1. Create a **custom class** that will hold the data that you want to visualize.
2. [Build a custom **materializer**](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md#custom-materializers) for this custom class with the visualization logic implemented in the `save_visualizations()` method.
3. Return your custom class from any of your ZenML steps.

### Example: Facets Data Skew Visualization

As an example, have a look at the models, materializers, and steps of the [Facets Integration](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-facets), which can be used to visualize the data skew between multiple Pandas DataFrames:

![Facets Visualization](../../.gitbook/assets/facets-visualization.png)

**1. Custom Class** The [FacetsComparison](https://sdkdocs.zenml.io/0.42.0/integration\_code\_docs/integrations-facets/#zenml.integrations.facets.models.FacetsComparison) is the custom class that holds the data required for the visualization.

```python
class FacetsComparison(BaseModel):
    datasets: List[Dict[str, Union[str, pd.DataFrame]]]
```

**2. Materializer** The [FacetsMaterializer](https://sdkdocs.zenml.io/0.42.0/integration\_code\_docs/integrations-facets/#zenml.integrations.facets.materializers.facets\_materializer.FacetsMaterializer) is a custom materializer that only handles this custom class and contains the corresponding visualization logic.

```python
class FacetsMaterializer(BaseMaterializer):

    ASSOCIATED_TYPES = (FacetsComparison,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def save_visualizations(
        self, data: FacetsComparison
    ) -> Dict[str, VisualizationType]:
        html = ...  # Create a visualization for the custom type 
        visualization_path = os.path.join(self.uri, VISUALIZATION_FILENAME)
        with fileio.open(visualization_path, "w") as f:
            f.write(html)
        return {visualization_path: VisualizationType.HTML}
```

**3. Step** There are three different steps in the `facets` integration that can be used to create `FacetsComparison`s for different sets of inputs. E.g., the `facets_visualization_step` below takes two DataFrames as inputs and builds a `FacetsComparison` object out of them:

```python
@step
def facets_visualization_step(
    reference: pd.DataFrame, comparison: pd.DataFrame
) -> FacetsComparison:  # Return the custom type from your step
    return FacetsComparison(
        datasets=[
            {"name": "reference", "table": reference},
            {"name": "comparison", "table": comparison},
        ]
    )
```

{% hint style="info" %}
This is what happens now under the hood when you add the `facets_visualization_step` into your pipeline:

1. The step creates and returns a `FacetsComparison`.
2. When the step finishes, ZenML will search for a materializer class that can handle this type, finds the `FacetsMaterializer`, and calls the `save_visualizations()` method which creates the visualization and saves it into your artifact store as an HTML file.
3. When you open your dashboard and click on the artifact inside the run DAG, the visualization HTML file is loaded from the artifact store and displayed.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
