---
description: Integrating unit testing in your ZenML pipeline.
---

acknowledgement: [Fussylabs MindGPT](https://github.com/fuzzylabs/MindGPT/tree/develop/tests/test_steps)

# Write unit testing
In ZenML, unit testing plays a crucial role in ensuring the robustness and reliability of machine learning pipelines. Sometimes, it can be beneficial to extract common functionalities into separate functions to prevent code duplication and streamline the pipeline development process. This approach not only enhances code readability but also simplifies the testing phase by isolating specific functionalities for testing.

## Why unit testing is required?
Unit testing is essential for ensuring the reliability and correctness of individual components within pipelines. It serves as a quality assurance mechanism, validating that each step, like data loaders or transformations does their job as intended in isolation. Unit tests provide an additional layer of confidence by verifying specific functionalities, catching bugs early in the development cycle, and enabling easier troubleshooting. By confirming that each unit operates correctly independent of the entire pipeline, it promotes robustness, enhances maintainability, and fosters a more efficient development process within ZenML.

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

    # We can call any ZenML step directly as a normal Python function
    result = calculate_means(test_list)

    assert result == expected_result

```

For running unit test, we can then execute `pytest test_embeddings_step.py` which will invoke the pytest framework to run the tests and show relevant output.


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