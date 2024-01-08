---
description: Integrating unit testing in your ZenML pipeline.
---

# Write unit testing
In ZenML, unit testing plays a crucial role in ensuring the robustness and reliability of machine learning pipelines. Sometimes, it can be beneficial to extract common functionalities into separate functions to prevent code duplication and streamline the pipeline development process. This approach not only enhances code readability but also simplifies the testing phase by isolating specific functionalities for testing.

# Why unit testing is required?
Unit testing is essential for ensuring the reliability and correctness of individual components within pipelines. It serves as a quality assurance mechanism, validating that each step, like data loaders or transformations, functions as intended in isolation. Unit tests provide an additional layer of confidence by verifying specific functionalities, catching bugs early in the development cycle, and enabling easier troubleshooting. By confirming that each unit operates correctly independent of the entire pipeline, it promotes robustness, enhances maintainability, and fosters a more efficient development process within ZenML.

# How is unit testing is tested?
Unit testing in ZenML is carried out by writing test cases using frameworks like Pytest. These test cases focus on individual units, such as steps within pipelines, to validate their functionality in isolation. Test functions are created to check specific behaviors or inputs and ensure expected outputs. Mocking and patching are often used to simulate dependencies or external interactions, allowing thorough testing without affecting the actual environment. Continuous integration and deployment (CI/CD) pipelines further automate the execution of these tests, running them regularly to guarantee ongoing code stability and reliability in ZenML's development cycle.

For more practical view, Let's say this our ZenML step code:

```python
@step(enable_cache=False)
def step_2(input_one: str, input_two: str) -> None:
    """Combines the two strings passed in."""
    combined_str = f"{input_one} {input_two}"
    return combined_str
```

This is a ZenML step and you might want to make sure that this step is working properly, and if incase it doesn't work by any chance, You want to be known very first rather then after having some disaster. So for this you need write some unit testing in function, each function is one test cases. Although you can write function according to your requirement but, it is recommended to write one test case in one function as it is named Unit testing not integrated testing. As the when the unit testing functions are runned it shows `no. of testcases passed!` in terminal.

So, here is the unit testing for your ZenML step code written above.

```Python
def test_step_2():
    input_one = "Hello"
    input_two = "World"

    combined_str = step_2(input_one, input_two)

    assert combined_str == "Hello World"

```
Let's say, Your test_step_2 code is kept in `test_step.py` file in same directory for running unit testing, we run it by using `pytest test_step.py` which will envoke your python testcases file to run and shows output.

<!--Reading Output-->

## Reading Output of Your ZenML Step

### Terminal Output Structure
When running ZenML steps, the terminal output is organized to provide information about the test session, test platform, and test results. Here's a breakdown of the structure:

- **Test Session Start**: The initial section displays information about the test session, including platform details, Python version, pytest version, and any loaded plugins.
- **Collected Items**: This section indicates the number of collected test items or test cases found in the specified directory. It displays progress as each test case is executed.
- **Test Results**: After the execution, the output shows the test results, including the number of passed, failed, or skipped test cases and their corresponding percentage of completion. Each dot represents a successfully executed test case.

### Example Output Structure

```plaintext
============================================ test session starts =============================================
platform win32 -- Python, pytest, pluggy
rootdir: C:\your_directory
plugins: anyio-4.2.0
collected 2 items

main.py ..                                                                                              [100%] 

============================================= 2 passed in 0.04s ==============================================
```

### Interpretation Guide

- **Platform**: Displays the operating system (`win32`) and the Python version (`3.12.1`) used for testing.
- **Test Collection**: Shows the number of collected items or test cases found (`2 items`) and their execution progress (`..`).
- **Execution Status**: `[100%]` signifies that all test cases have completed. The dots represent passed tests (`.`).
- **Summary**: Indicates the test outcome—`2 passed` test cases—in a specified duration (`0.04s`).

### Understanding Results

- **Passed**: The number of test cases that ran successfully.
- **Failed/Skipped**: Any test cases that did not pass or were skipped during execution.
- **Execution Time**: The time taken to execute the entire test suite.

# Some tips and best practices to follow while writing unit testing for ZenML

- Isolation : Ensure each test is independent and doesn't rely on external dependencies or other test cases for its execution. This prevents cascading failures and makes debugging easier.

- Truly unit, not integration: As discussed earlier unit test is supposed to have one testcases as one function and more parts of code to be tested from one function. Since it is unit testing not integration testing

- Fast : It is crucial to have fast running unit test as a project can have thousands of unit tests or may be even more, in that slow running sluggish unit tests can frustate tester. Sometime being frustated tester may skip them.

- Clarity and Readability: Write clear, descriptive test names that explain the purpose of the test. Use comments and docstrings to describe complex scenarios or the expected behavior being tested.

- Single Responsibility Principle: Focus each test on a specific scenario or functionality. Avoid testing multiple behaviors in one test case.

- Setup and Teardown:Set up necessary preconditions for the test and clean up after the test completes. Use setup and teardown methods or fixtures to manage test data and resources.

- Coverage and Edge Cases: Aim for comprehensive test coverage. Test both typical use cases and edge cases, including boundary conditions and scenarios where the behavior might break.

- Use Mocks and Stubs: Employ mocking libraries to simulate external dependencies, APIs, or complex systems. This helps isolate the unit under test and ensures predictable behavior.

- Assertions: Use clear and specific assertions to validate the expected behavior of the code. Choose appropriate assertions that match the context of the test.

- Avoid Testing Framework Logic: Unit tests should focus on the application's logic, not the underlying testing framework. Minimize assertions about the framework itself.

- Performance: Ensure tests execute quickly. Slow tests can discourage frequent execution and slow down the development cycle.

- Maintainability: Regularly review and refactor tests to keep them up to date with code changes. Remove redundant or obsolete tests to maintain a manageable test suite.

- Continuous Integration (CI): Integrate tests into a CI/CD pipeline to automate test execution on code changes, ensuring new code doesn't break existing functionality.

- Documentation and Reporting: Provide clear instructions on how to run tests, interpret results, and generate reports. Document the purpose and scope of each test suite or test case.

- Avoid logic in tests: Unit test should be simple, succint and easy to understand, Writing logic in tests increases chances of having bugs in your unit test's code. If logic in a test cases seems, try spliting tests in two or more different tests.

- Keep your tests away from too much implementation details: Your unit tests should rarely fail when slightest change in implemented code is done, or else it will be difficult to maintain. The optimal approach is to steer clear of implementation details to avoid the need for rewriting tests repeatedly. Coupling tests with implementation specifics diminishes the efficacy of the tests.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>