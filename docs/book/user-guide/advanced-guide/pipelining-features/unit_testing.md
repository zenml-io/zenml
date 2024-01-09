---
description: Integrating unit testing in your ZenML pipeline.
---

# Write unit testing
In ZenML, unit testing plays a crucial role in ensuring the robustness and reliability of machine learning pipelines. Sometimes, it can be beneficial to extract common functionalities into separate functions to prevent code duplication and streamline the pipeline development process. This approach not only enhances code readability but also simplifies the testing phase by isolating specific functionalities for testing.

## Why unit testing is required?
Unit testing is essential for ensuring the reliability and correctness of individual components within pipelines. It serves as a quality assurance mechanism, validating that each step, like data loaders or transformations does their job as intended in isolation. Unit tests provide an additional layer of confidence by verifying specific functionalities, catching bugs early in the development cycle, and enabling easier troubleshooting. By confirming that each unit operates correctly independent of the entire pipeline, it promotes robustness, enhances maintainability, and fosters a more efficient development process within ZenML.

## How is unit testing is tested?
Unit testing in ZenML can be carried out by writing test cases using frameworks like Pytest. These test cases focus on individual units, such as steps within pipelines, to validate their functionality in isolation. Test functions are created to check specific behaviors or inputs and ensure expected outputs. Mocking and patching are often used to simulate dependencies or external interactions, allowing thorough testing without affecting the actual environment. Continuous integration and deployment (CI/CD) pipelines further automate the execution of these tests, running them regularly to guarantee ongoing code stability and reliability in ZenML's development cycle.

For more practical view, this is our ZenML step code:

```python
@step(enable_cache=False)
def step_2(input_one: str, input_two: str) -> None:
    """Combines the two strings passed in."""
    combined_str = f"{input_one} {input_two}"
    return combined_str
```

This is a ZenML step, and ensuring its proper functionality is crucial. In case it fails, you want to detect this issue early to prevent potential disasters. To achieve this, writing unit tests for each function is necessary. While you have the flexibility to structure functions based on your needs, it's advisable to follow a one-test-case-per-function approach. This practice aligns with the principles of unit testing, focusing on individual functionalities rather than integration. When running these unit test functions, the terminal displays the count of passed test cases.

So, here is the unit testing for your ZenML step code written above.

```Python
def test_step_2():
    input_one = "Hello"
    input_two = "World"
    import test_step #file name
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

## Some tips and best practices to follow while writing unit testing for ZenML

### Isolation:
Ensure each test is independent and doesn't rely on external dependencies or other test cases for its execution. This prevents cascading failures and makes debugging easier.

```Python
import unittest
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.evaluator.tf_evaluator import TFEvaluator
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.preprocesser.standard_scaler import StandardScaler
from zenml.core.steps.trainer.tf_trainer import TFTrainer
from unittest.mock import patch, MagicMock

class TestZenMLIsolation(unittest.TestCase):
    
    def setUp(self):
        # Initialize your ZenML objects
        self.datasource_mock = MagicMock()
        self.split_mock = MagicMock()
        self.preprocess_mock = MagicMock()
        self.trainer_mock = MagicMock()
        self.evaluator_mock = MagicMock()
        
    def test_pipeline_steps_isolation(self):
        # Create a training pipeline
        training_pipeline = TrainingPipeline(name='my_training_pipeline',
                                             datasource=self.datasource_mock,
                                             steps=[self.split_mock,
                                                    self.preprocess_mock,
                                                    self.trainer_mock,
                                                    self.evaluator_mock])
        
        # Set isolation for each step in the pipeline
        for step in training_pipeline.steps:
            self.assertTrue(step.isolation, msg=f"{step} is not isolated.")
            
    def test_step_isolation(self):
        # Create individual steps
        split = RandomSplit()
        preprocess = StandardScaler()
        trainer = TFTrainer()
        evaluator = TFEvaluator()
        
        # Set isolation for each step individually
        split.isolation = True
        preprocess.isolation = True
        trainer.isolation = True
        evaluator.isolation = True
        
        self.assertTrue(split.isolation, msg="RandomSplit step is not isolated.")
        self.assertTrue(preprocess.isolation, msg="StandardScaler step is not isolated.")
        self.assertTrue(trainer.isolation, msg="TFTrainer step is not isolated.")
        self.assertTrue(evaluator.isolation, msg="TFEvaluator step is not isolated.")
        
if __name__ == '__main__':
    unittest.main()
```

We imported the necessary ZenML classes and unittest module.
We create a `TestZenMLIsolation` class that inherits from `unittest.TestCase`.
In the setUp method, we initialized mock objects for the ZenML pipeline components to be tested.
Two test methods defined in code above are:
1. `test_pipeline_steps_isolation`: Ensures that isolation is set for each step within a training pipeline. 

2. `test_step_isolation` : Checks individual step isolation by creating steps separately and verifying their isolation property.

These tests use assertions (assertTrue) to validate whether isolation is properly set for each step in the pipeline or for individual steps. This approach helps ensure that the tests are independent of each other and don't rely on external dependencies, adhering to the isolation best practice in unit testing for ZenML.

### Truly unit, not integration:
As discussed earlier, a unit test should consist of one test case per function, focusing on testing individual parts of code within that function. This approach aligns with the concept of unit testing, distinguishing it from integration testing.

```Python
import unittest
from zenml.core.datasources.base_datasource import BaseDatasource
from unittest.mock import MagicMock

class TestCustomDatasource(unittest.TestCase):
    
    def test_custom_datasource_behavior(self):
        # Mocking external dependencies or connections
        external_dependency_mock = MagicMock()
        
        # Create an instance of your custom datasource class
        custom_datasource = CustomDatasource(external_dependency=external_dependency_mock)
        
        # For example, let's assume a method `fetch_data` fetches data
        data = custom_datasource.fetch_data()
        
        # Assert expected behavior based on the mocked response or behavior
        self.assertIsNotNone(data, msg="Data fetching failed.")
        
if __name__ == '__main__':
    unittest.main()

```
We created a `TestCustomDatasource` class inheriting from unittest.TestCase. The `test_custom_datasource_behavior` function tests the behavior of a custom datasource class,assuming a `method fetch_data()` is responsible for fetching data. Using MagicMock, we mock any external dependencies or connections that the custom datasourcemight have, ensuring isolation from these external components. Within the test function, we call the `fetch_data()` method and perform assertions based onexpected behavior.

This approach ensures that the test is focused on the behavior of the specific component (CustomDatasource in this case) and doesn't rely on real external connections or dependencies. It verifies the functionality of a single function or method within the CustomDatasource class, maintaining the principles of true unit testing in ZenML.


- Fast : It is crucial to have fast running unit test as a project can have thousands of unit tests or may be even more, in that slow running sluggish unit tests can frustate tester. Sometime being frustated tester may skip them.

```Python
import unittest
from zenml.core.steps.trainer.tf_trainer import TFTrainer
from unittest.mock import MagicMock

class TestTFTrainer(unittest.TestCase):
    
    def setUp(self):
        # Mock necessary dependencies or connections to speed up tests
        self.model_mock = MagicMock()
        self.training_data_mock = MagicMock()
        self.training_args_mock = MagicMock()
        
    def test_tf_trainer_speed(self):
        # Create an instance of TFTrainer with mocked dependencies
        trainer = TFTrainer(model=self.model_mock,
                            training_data=self.training_data_mock,
                            training_args=self.training_args_mock)
        
        # Measure the time taken for training
        import time
        start_time = time.time()
        trainer.train()
        end_time = time.time()
        
        # Set a threshold for maximum allowed execution time
        max_allowed_time = 5.0  # in seconds
        
        # Check if the execution time is within the threshold
        execution_time = end_time - start_time
        self.assertLessEqual(execution_time, max_allowed_time,
                             msg=f"Training took too long ({execution_time} s).")
        
if __name__ == '__main__':
    unittest.main()

```

The TestTFTrainer class contains a test method test_tf_trainer_speed that measures the time taken by the train() method of the TFTrainer class to ensure it executes within an acceptable threshold.
In the setUp method, necessary dependencies for the TFTrainer instance are mocked using MagicMock. This ensures that the test focuses solely on the speed of the training process rather than the actual training with real data, which might take longer.
It uses time.time() to measure the start and end times of the train() method and compares the execution time against a predefined maximum allowed time (max_allowed_time).
The assertLessEqual() method checks whether the execution time is within the specified threshold. If the training process exceeds the threshold, the test will fail, indicating that the training process might be too slow.

By focusing on testing specific functionalities related to speed and mocking external dependencies, these tests can execute quickly, ensuring that they do not frustrate testers or developers due to excessive execution times. Adjust the max_allowed_time as needed based on your performance expectations.
 


### Clarity and Readability: 
Write clear, descriptive test names that explain the purpose of the test. Use comments and docstrings to describe complex scenarios or the expected behavior being tested.

```Python
import unittest
from zenml.core.steps.preprocesser.standard_scaler import StandardScaler
from unittest.mock import MagicMock

class TestStandardScaler(unittest.TestCase):
    
    def setUp(self):
        # Mock necessary dependencies or connections
        self.input_data_mock = MagicMock()
        
    def test_standard_scaler_with_positive_values(self):
        """Test StandardScaler with positive input values."""
        # Create an instance of StandardScaler with mocked input data
        scaler = StandardScaler()
        
        # Assuming transform() method applies scaling
        scaled_data = scaler.transform(self.input_data_mock)
        
        # Add assertions specific to positive input values
        # For instance, check if the scaled values are within expected ranges
        # Add comments for clarity on the expected behavior
        
        # Assert statements
        self.assertIsNotNone(scaled_data, msg="Scaled data is None.")
        # Add more assertions as per specific behavior
        # For example, assuming the scale is between 0 and 1
        self.assertTrue(all(0 <= val <= 1 for val in scaled_data), 
                        msg="Scaled values are not within expected range.")
        
    def test_standard_scaler_with_negative_values(self):
        """Test StandardScaler with negative input values."""
        # Create an instance of StandardScaler with mocked input data
        scaler = StandardScaler()
        
        # Assuming transform() method applies scaling
        scaled_data = scaler.transform(self.input_data_mock)
        
        # Add assertions specific to negative input values
        
        # Assert statements
        self.assertIsNotNone(scaled_data, msg="Scaled data is None.")
        # Add more assertions as per specific behavior
        
    def test_standard_scaler_with_mixed_values(self):
        """Test StandardScaler with mixed positive and negative input values."""
        # Create an instance of StandardScaler with mocked input data
        scaler = StandardScaler()
        
        # Assuming transform() method applies scaling
        scaled_data = scaler.transform(self.input_data_mock)
        
        # Add assertions specific to mixed input values
        
        # Assert statements
        self.assertIsNotNone(scaled_data, msg="Scaled data is None.")
        # Add more assertions as per specific behavior
        
    def test_standard_scaler_with_empty_input(self):
        """Test StandardScaler with empty input."""
        # Create an instance of StandardScaler with mocked input data
        scaler = StandardScaler()
        
        # Assuming transform() method applies scaling
        scaled_data = scaler.transform(self.input_data_mock)
        
        # Add assertions specific to empty input
        
        # Assert statements
        self.assertIsNotNone(scaled_data, msg="Scaled data is None.")
        # Add more assertions as per specific behavior
        
if __name__ == '__main__':
    unittest.main()

```

Each test method has a clear and descriptive name, such as test_standard_scaler_with_positive_values, test_standard_scaler_with_negative_values, etc., explaining the scenario being tested.
Docstrings are used to provide additional clarity on the purpose of each test method. They describe the specific scenario being tested, for instance, testing with positive values, negative values, mixed values, or empty inputs.
Comments within the test methods guide the reader through the test logic, indicating where assertions or specific test conditions should be placed and explaining the expected behavior.

By employing descriptive test names, informative docstrings, and clear comments, these practices significantly enhance the readability and understanding of the test suite, making it easier for developers to comprehend the purpose and expected behavior of each test case.



- Single Responsibility Principle: Focus each test on a specific scenario or functionality. Avoid testing multiple behaviors in one test case.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up test data or mock necessary dependencies
        self.input_data = [1, 2, 3, 4, 5]
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        # Create an instance of DataProcessor
        processor = DataProcessor()
        
        # Assuming the `calculate_sum()` method calculates the sum of input data
        result = processor.calculate_sum(self.input_data)
        
        # Add assertions specific to sum calculation
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        # Create an instance of DataProcessor
        processor = DataProcessor()
        
        # Assuming the `calculate_average()` method calculates the average of input data
        result = processor.calculate_average(self.input_data)
        
        # Add assertions specific to average calculation
        self.assertEqual(result, 3, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        # Create an instance of DataProcessor
        processor = DataProcessor()
        
        # Assuming the `calculate_median()` method calculates the median of input data
        result = processor.calculate_median(self.input_data)
        
        # Add assertions specific to median calculation
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```
Three separate test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, and test_data_processor_median_calculation) are created, each focusing on testing a specific functionality (sum calculation, average calculation, and median calculation) of the DataProcessor class.
The setUp method initializes the test data or necessary dependencies shared across the test methods.
Each test method creates an instance of DataProcessor and calls a specific method (calculate_sum, calculate_average, or calculate_median) to test a particular behavior, followed by specific assertions for that behavior.

By adhering to the Single Responsibility Principle in testing, each test method focuses on testing a specific scenario or functionality, ensuring clear separation of concerns and better maintainability of the test suite.


- Setup and Teardown:Set up necessary preconditions for the test and clean up after the test completes. Use setup and teardown methods or fixtures to manage test data and resources.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        self.test_data = [1, 2, 3, 4, 5]
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        self.test_data = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        # Assuming the `calculate_sum()` method calculates the sum of input data
        result = self.processor.calculate_sum(self.test_data)
        
        # Add assertions specific to sum calculation
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        # Assuming the `calculate_average()` method calculates the average of input data
        result = self.processor.calculate_average(self.test_data)
        
        # Add assertions specific to average calculation
        self.assertEqual(result, 3, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        # Assuming the `calculate_median()` method calculates the median of input data
        result = self.processor.calculate_median(self.test_data)
        
        # Add assertions specific to median calculation
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```
The setUp method is used to set up preconditions necessary for each test method. Here, it creates an instance of DataProcessor and initializes self.test_data.
The tearDown method is used to clean up or release resources after each test method completes. Here, it resets the self.processor and self.test_data variables to None.
Three test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, and test_data_processor_median_calculation) utilize the setup by accessing the DataProcessor instance and the test data, performing specific calculations, and making assertions.

Using setUp and tearDown methods ensures that the test environment is appropriately set up before each test and cleaned up afterward, maintaining a consistent and isolated environment for each individual test method.


- Coverage and Edge Cases: Aim for comprehensive test coverage. Test both typical use cases and edge cases, including boundary conditions and scenarios where the behavior might break.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_sum(test_data)
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        # Test case with an empty list
        empty_list = []
        result_empty_list = self.processor.calculate_average(empty_list)
        self.assertEqual(result_empty_list, 0, msg="Average of empty list should be 0.")
        
        # Test case with a list of identical values
        identical_values_list = [3, 3, 3, 3, 3]
        result_identical_values_list = self.processor.calculate_average(identical_values_list)
        self.assertEqual(result_identical_values_list, 3, msg="Average of identical values list failed.")
        
        # Test case with a list of odd number of values
        odd_number_values_list = [1, 2, 3, 4, 5]
        result_odd_number_values_list = self.processor.calculate_average(odd_number_values_list)
        self.assertEqual(result_odd_number_values_list, 3, msg="Average calculation for odd number of values failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        # Test case with an even number of values
        even_number_values_list = [1, 2, 3, 4]
        result_even_number_values_list = self.processor.calculate_median(even_number_values_list)
        self.assertEqual(result_even_number_values_list, 2.5, msg="Median calculation for even number of values failed.")
        
        # Test case with an odd number of values
        odd_number_values_list = [1, 2, 3, 4, 5]
        result_odd_number_values_list = self.processor.calculate_median(odd_number_values_list)
        self.assertEqual(result_odd_number_values_list, 3, msg="Median calculation for odd number of values failed.")
        
        # Test case with an empty list
        empty_list = []
        result_empty_list = self.processor.calculate_median(empty_list)
        self.assertIsNone(result_empty_list, msg="Median of empty list should be None.")
        
if __name__ == '__main__':
    unittest.main()

```
In this example:

Three test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, and test_data_processor_median_calculation) are created, each testing a specific functionality of the DataProcessor class.
The setUp method initializes the DataProcessor instance before each test method.
The tearDown method cleans up resources after each test method completes.
Each test method covers typical use cases (e.g., sum, average, and median calculations) and various edge cases such as empty lists, lists with identical values, odd and even number of values, ensuring comprehensive test coverage.

By considering different scenarios, including edge cases and boundary conditions, this test suite ensures thorough coverage of the DataProcessor class, addressing both typical use cases and scenarios where the behavior might break.


- Use Mocks and Stubs: Employ mocking libraries to simulate external dependencies, APIs, or complex systems. This helps isolate the unit under test and ensures predictable behavior.
```Python
import unittest
from unittest.mock import MagicMock
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        # Mock the data for calculation
        test_data = [1, 2, 3, 4, 5]
        # Mocking the external dependency (if any) used in the calculation
        self.processor.calculate_sum = MagicMock(return_value=sum(test_data))
        
        result = self.processor.calculate_sum(test_data)
        # Ensure that the mocked method was called with the correct data
        self.processor.calculate_sum.assert_called_once_with(test_data)
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        # Mock the data for calculation
        test_data = [1, 2, 3, 4, 5]
        # Mocking the external dependency (if any) used in the calculation
        self.processor.calculate_average = MagicMock(return_value=sum(test_data) / len(test_data))
        
        result = self.processor.calculate_average(test_data)
        # Ensure that the mocked method was called with the correct data
        self.processor.calculate_average.assert_called_once_with(test_data)
        self.assertEqual(result, 3, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        # Mock the data for calculation
        test_data = [1, 2, 3, 4, 5]
        # Mocking the external dependency (if any) used in the calculation
        # Here, using the `sort()` method to simulate the median calculation
        self.processor.calculate_median = MagicMock(return_value=sorted(test_data)[len(test_data)//2])
        
        result = self.processor.calculate_median(test_data)
        # Ensure that the mocked method was called with the correct data
        self.processor.calculate_median.assert_called_once_with(test_data)
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```
    Three test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, and test_data_processor_median_calculation) are created, each testing a specific functionality of the DataProcessor class while using mocks.
    For each test method, the MagicMock object is utilized to mock the behavior of the method being tested (calculate_sum, calculate_average, or calculate_median) within the DataProcessor class.
    The mocked method is set to return specific values that simulate the behavior of the actual method, ensuring predictable behavior in the tests.
    Assertions are made to verify that the mocked methods were called with the correct data, ensuring that the expected calculations were performed.

By employing mocks and stubs, this test suite isolates the unit under test (DataProcessor) from its dependencies, enabling focused testing and ensuring predictable behavior without relying on external factors.


- Assertions: Use clear and specific assertions to validate the expected behavior of the code. Choose appropriate assertions that match the context of the test.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_sum(test_data)
        
        # Use specific assertions to validate the expected behavior
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_average(test_data)
        
        # Use appropriate assertions to verify the average calculation
        self.assertAlmostEqual(result, 3, places=2, msg="Average calculation failed.")
        # Here, `assertAlmostEqual` checks if the result is approximately equal to 3
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_median(test_data)
        
        # Use specific assertions to validate the expected behavior
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```
Three test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, and test_data_processor_median_calculation) are created, each focusing on testing a specific functionality of the DataProcessor class.
Within each test method, clear and specific assertions (self.assertEqual, self.assertAlmostEqual) are used to validate the expected behavior of the calculations performed by the DataProcessor.
The assertions check if the results match the expected outcomes for sum, average, and median calculations, ensuring the correctness of the functionality being tested.

By using appropriate assertions (self.assertEqual, self.assertAlmostEqual, etc.) that match the context of the test, this test suite ensures that the expected behavior of the DataProcessor class is validated accurately.


- Avoid Testing Framework Logic: Unit tests should focus on the application's logic, not the underlying testing framework. Minimize assertions about the framework itself.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_sum(test_data)
        
        # Use specific assertions to validate the expected behavior
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_average(test_data)
        
        # Use appropriate assertions to verify the average calculation
        self.assertAlmostEqual(result, 3, places=2, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        test_data = [1, 2, 3, 4, 5]
        result = self.processor.calculate_median(test_data)
        
        # Use specific assertions to validate the expected behavior
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```
The focus remains solely on testing the DataProcessor class logic through its methods (calculate_sum, calculate_average, calculate_median) without assertions regarding the testing framework.
The test methods (test_data_processor_sum_calculation, test_data_processor_average_calculation, test_data_processor_median_calculation) perform specific calculations and use assertions (self.assertEqual, self.assertAlmostEqual) to validate the expected behavior of the DataProcessor class.
The test suite avoids making assertions or validations about the underlying testing framework (unittest.TestCase) and maintains a focus on the logic and behavior of the application code being tested.


- Performance: Ensure tests execute quickly. Slow tests can discourage frequent execution and slow down the development cycle.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        self.test_data = [1, 2, 3, 4, 5]
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        self.test_data = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        result = self.processor.calculate_sum(self.test_data)
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        result = self.processor.calculate_average(self.test_data)
        self.assertAlmostEqual(result, 3, places=2, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        result = self.processor.calculate_median(self.test_data)
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
if __name__ == '__main__':
    unittest.main()

```

Tests are organized efficiently, each focusing on a specific functionality of the DataProcessor class (calculate_sum, calculate_average, calculate_median).
The setUp method initializes necessary resources for each test method, preventing unnecessary repetitive setup.
The tearDown method cleans up resources after each test, ensuring a clean state for subsequent tests.
Assertions (self.assertEqual, self.assertAlmostEqual) are used to verify the expected behavior of the DataProcessor class.
By focusing on testing specific functionalities and avoiding excessive setup/teardown or unnecessary complexity, these tests are designed to execute quickly, promoting frequent execution during development without slowing down the cycle.


- Maintainability: Regularly review and refactor tests to keep them up to date with code changes. Remove redundant or obsolete tests to maintain a manageable test suite.

```Python
import unittest
from zenml.core.steps.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        # Set up any necessary preconditions or resources before each test method
        self.processor = DataProcessor()
        self.test_data = [1, 2, 3, 4, 5]
        
    def tearDown(self):
        # Clean up or release any resources after each test method completes
        self.processor = None
        self.test_data = None
        
    def test_data_processor_sum_calculation(self):
        """Test DataProcessor for correct sum calculation."""
        result = self.processor.calculate_sum(self.test_data)
        self.assertEqual(result, 15, msg="Sum calculation failed.")
        
    def test_data_processor_average_calculation(self):
        """Test DataProcessor for correct average calculation."""
        result = self.processor.calculate_average(self.test_data)
        self.assertAlmostEqual(result, 3, places=2, msg="Average calculation failed.")
        
    def test_data_processor_median_calculation(self):
        """Test DataProcessor for correct median calculation."""
        result = self.processor.calculate_median(self.test_data)
        self.assertEqual(result, 3, msg="Median calculation failed.")
        
    # Hypothetical additional test, currently commented out
    # def test_data_processor_invalid_input(self):
    #     """Test DataProcessor for handling invalid input."""
    #     invalid_data = 'invalid_data'
    #     with self.assertRaises(ValueError):
    #         self.processor.calculate_sum(invalid_data)
        
if __name__ == '__main__':
    unittest.main()

```
    The test suite contains three well-defined test methods focusing on specific functionalities of the DataProcessor.
    To maintain readability and manageability, a hypothetical additional test (test_data_processor_invalid_input) is commented out. It may be obsolete or needs revision to align with code changes.
    Periodically reviewing and uncommenting or updating such tests when relevant ensures the test suite remains aligned with code changes and covers relevant scenarios without cluttering obsolete tests.
    Regularly reviewing and revising tests, removing redundant or obsolete ones, and updating tests to align with code changes contribute to a maintainable and effective test suite.


- Continuous Integration (CI): Integrate tests into a CI/CD pipeline to automate test execution on code changes, ensuring new code doesn't break existing functionality.

- Documentation and Reporting: Provide clear instructions on how to run tests, interpret results, and generate reports. Document the purpose and scope of each test suite or test case.

### Avoid logic in tests: 
Unit test should be simple, succint and easy to understand, Writing logic in tests increases chances of having bugs in your unit test's code. If logic in a test cases seems, try spliting tests in two or more different tests.

### Keep your tests away from too much implementation details: 
Your unit tests should rarely fail when slightest change in implemented code is done, or else it will be difficult to maintain. The optimal approach is to steer clear of implementation details to avoid the need for rewriting tests repeatedly. Coupling tests with implementation specifics diminishes the efficacy of the tests.


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>