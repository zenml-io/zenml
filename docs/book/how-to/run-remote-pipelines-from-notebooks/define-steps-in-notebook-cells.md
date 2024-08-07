
# Define steps in notebook cells

If you want to run ZenML steps defined in notebook cells remotely (either with a remote [orchestrator](../../component-guide/orchestrators/orchestrators.md) or [step operator](../../component-guide/step-operators/step-operators.md)), the cells defining your steps must meet the following conditions:
- The cell can only contain python code, no Jupyter magic commands or shell commands starting with a `%` or `!`
- The cell **must not** call code from other notebook cells. Functions or classes defined in python files are okay to use.
- The cell **must not** rely on imports of previous cells. This means your cell must perform all the imports it needs itself, including ZenML imports like `from zenml import step`

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>