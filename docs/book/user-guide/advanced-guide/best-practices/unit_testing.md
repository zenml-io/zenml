---
description: Integrating unit testing in your ZenML pipeline.
---

acknowledgement: [Fuzzylabs MindGPT](https://github.com/fuzzylabs/MindGPT/tree/develop/tests/test_steps)

# Write unit testing
Unit testing in ZenML can be done by using different methodologies. Since, ZenML steps and pipelines are python function itself. Since, ZenML pipelines are python function, we can employ various methodologies for testing ZenML steps and pipelines.  

## How to do unit test?
Unit testing in ZenML can be carried out by writing test cases using frameworks like Pytest. These test cases focus on individual units, such as steps within pipelines, to validate their functionality in isolation. Test functions are created to check specific behaviors or inputs and ensure expected outputs. 

For a more practical view, let's say this is our code:

```python
def calculate_means(embeddings: List[List[float]]) -> List[float]:
    """Calculate the mean of each list of embeddings.

    Args:
        embeddings (List[List[float]]): a list of lists, where each inner list contains floats

    Returns:
        List[float]: the mean of each list of embeddings.
    """
    return [mean(embedding) for embedding in embeddings]
```

This is a python code and ensuring its proper functionality is crucial. In case it fails, we want to detect early to prevent potential disasters.

So, here is the corresponding unit test of the above step:

```Python
from test_step_2 import calculate_means
def test_calculate_means():
    """Test that the calculate_means function is able to return expected result."""
    test_list = [[1, 1, 1], [2, 2, 2], [1.5, 2.5, 3.5]]
    expected_result = [1, 2, 2.5]

    result = calculate_means(test_list)

    assert result == expected_result

```

Let's say, Your `test_step_2` code is kept in `test_step.py` file in same directory. For running unit test for that `calculate_means` function, we use  `pytest test_step.py` which will envoke your python testcases file to run and show output.

### Some examples of unit testing in ZenML steps and pipelines

```Python
from unittest.mock import patch
import pytest
import yaml
from zenml import get_step_context, pipeline, step
from zenml.client import Client
from zenml.model.model_version import ModelVersion
```
We have also imported patch from mock library of unittest library. `patch` is a function provided by the `unittest.mock` module in Python. It is commonly used for temporarily modifying or replacing the behaviour of objects during testing.\
We have also imported the `unittest` and `pytest` libraries, along with other necessary libraries, for creating ZenML steps ,pipelines and testing it.

```Python
@step
def assert_model_version_step():
    model_version = get_step_context().model_version
    assert model_version is not None
    assert model_version.name == "foo"
    assert model_version.version == str(model_version.number)
    assert model_version.description == "description"
    assert model_version.license == "MIT"
    assert model_version.audience == "audience"
    assert model_version.use_cases == "use_cases"
    assert model_version.limitations == "limitations"
    assert model_version.trade_offs == "trade_offs"
    assert model_version.ethics == "ethics"
    assert model_version.tags == ["tag"]
    assert model_version.save_models_to_registry
```

This code defines a step in a process or workflow, and we are testing various aspects of this step. Specifically, we are checking properties of a model_version, such as its name, license, and other attributes, to make sure they meet our expectations. These tests help ensure that this step behaves correctly and has the right information during its execution.

```Python
def test_pipeline_with_model_version_from_yaml(
    clean_client: "Client", tmp_path
):
    """Test that the pipeline can be configured with a model version from a yaml file."""
    model_version = ModelVersion(
        name="foo",
        description="description",
        license="MIT",
        audience="audience",
        use_cases="use_cases",
        limitations="limitations",
        trade_offs="trade_offs",
        ethics="ethics",
        tags=["tag"],
        save_models_to_registry=True,
    )

    config_path = tmp_path / "config.yaml"
    file_config = dict(
        run_name="run_name_in_file",
        model_version=model_version.dict(),
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_model_version_pipeline():
        assert_model_version_step()

    assert_model_version_pipeline.with_options(model_version=model_version)()
    assert_model_version_pipeline.with_options(config_path=str(config_path))()
```
The test checks whether the pipeline can be configured with a model version, either directly or through a YAML configuration file. It ensures that the pipeline correctly handles model version information and that both configuration methods work as expected during execution.

```Python
def test_pipeline_config_from_file_not_overridden_for_extra(
    clean_client: "Client", tmp_path
):
    """Test that the pipeline can be configured with an extra
    from a yaml file, but the values from yaml are not overridden.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(run_name="run_name_in_file", extra={"a": 1})
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_extra_pipeline():
        assert_extra_step()

    p = assert_extra_pipeline.with_options(config_path=str(config_path))
    assert p.configuration.extra == {"a": 1}

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(extra={"a": 2})
        warning.assert_called_once()

    assert p.configuration.extra == {"a": 2}

    p()
```

The function `test_pipeline_config_from_file_not_overridden_for_extra` verifies that when configuring a pipeline from a YAML file, the extra parameter from the file is not overridden if a different value is provided during additional configuration. It checks that a warning is logged in this case and ensures that the final configuration reflects the expected values.

```Python
import pytest
import yaml

from zenml import (
    ModelVersion,
    get_pipeline_context,
    get_step_context,
    pipeline,
    step,
)
from zenml.client import Client
```
Again, we have imported necessary library like `pytest` for testing  our ZenML Step


```Python
@step
def assert_pipeline_context_in_step():
    with pytest.raises(RuntimeError, match="Inside a step"):
        get_pipeline_context()

    context = get_step_context()
    assert (
        context.pipeline.name == "assert_pipeline_context_in_pipeline"
    ), "Not accessible inside running step"
    assert (
        context.pipeline_run.config.enable_cache is False
    ), "Not accessible inside running step"
    assert context.pipeline_run.config.extra == {
        "foo": "bar"
    }, "Not accessible inside running step"
```
this code is a test that checks whether the get_pipeline_context() function raises the correct exception when called inside a step and verifies specific conditions of the step context and pipeline run configuration when the step is running.

This code snippet demonstrates how to conduct testing of ZenML client calls and functions like `log_artifact_metadata` using the `pytest` framework. By leveraging Python's mocking capabilities, it enables the isolation and testing of specific ZenML functionalities without relying on the actual ZenML backend infrastructure. 

```Python
import pytest
import yaml
from zenml import pipeline
from zenml.client import Client

def test_pipeline_config_from_file_not_overridden_for_extra(
    clean_client: "Client", tmp_path
):
    """Test that the pipeline can be configured with an extra
    from a yaml file, but the values from yaml are not overridden.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(run_name="run_name_in_file", extra={"a": 1})
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_extra_pipeline():
        assert_extra_step()

    p = assert_extra_pipeline.with_options(config_path=str(config_path))
    assert p.configuration.extra == {"a": 1}

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(extra={"a": 2})
        warning.assert_called_once()

    assert p.configuration.extra == {"a": 2}

    p()
```

## Some tips and best practices to follow while writing unit testing for ZenML

### Isolation:
Ensure each test is independent and doesn't rely on external dependencies or other test cases for its execution. This prevents cascading failures and makes debugging easier.

### Truly unit, not integration:
A unit test should consist of one test case per function, focusing on testing individual parts of code within that function. This approach aligns with the concept of unit testing, which also distinguishes it from integration testing.

### Fast :
It is crucial to have fast running unit test. As a project can have thousands of unit tests or may be even more, in that case slow running sluggish unit tests can frustate tester. Sometime tester might skip them.

### Clarity and Readability: 
Write clear, descriptive test names that explain the purpose of the test. Use comments and docstrings to describe complex scenarios or the expected behavior which is being tested.

### Single Responsibility Principle: 
Focus each test on a specific scenario or functionality. Avoid testing multiple behaviors in one test case.

### Setup and Teardown:
Set up all the necessary preconditions for the test and clean up after the test completes. This approach is called Setup and teardown method .Use setup and teardown methods or fixtures to manage test data and resources.

### Coverage and Edge Cases: 
Aim for comprehensive test coverage. Test both typical use cases and edge cases, including boundary conditions and scenarios where the behavior might break.

### Use Mocks and Stubs: 
Employ mocking libraries to simulate external dependencies, APIs, or complex systems. This helps isolate the unit under test and ensures predictable behavior.

### Assertions: 
Use clear and specific assertions to validate the expected behavior of the code. Choose appropriate assertions that match the context of the test.

### Avoid Testing Framework Logic: 
Unit tests should focus on the application's logic, not the underlying testing framework. Minimize assertions about the framework itself.

### Maintainability: 
Regularly review and refactor tests to keep them up to date with code changes. Remove redundant or obsolete tests to maintain a manageable test suite.

### Continuous Integration (CI): 
Integrate tests into a CI/CD pipeline to automate test execution on code changes which ensures new code doesn't break existing functionality.

### Documentation and Reporting: 
Provide clear instructions on how to run tests, interpret results, and generate reports. Document the purpose and scope of each test suite or test case.

### Avoid logic in tests: 
Unit test should be simple, succint and easy to understand, Writing logic in tests increases chances of having bugs in your unit test's code. If logic is reqquired in test cases then try spliting tests in two or more different tests.

### Keep your tests away from too much implementation details: 
Your unit tests should rarely fail when slightest change in implemented code is done, or else it will be difficult to maintain. The optimal approach is to steer clear of implementation details to avoid the need for rewriting tests repeatedly. Coupling tests with implementation specifics diminishes the efficacy of the tests.


## Acknowledgments

If you have further inquiries or wish to explore unit testing approach in detail, you can refer to [FussyLab's MindGPT project](https://github.com/fuzzylabs/MindGPT/tree/develop/tests/test_steps) for insightful examples.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>