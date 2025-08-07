#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for the Prompt Materializer."""

from datetime import datetime

from tests.unit.test_general import _test_materializer
from zenml.materializers.prompt_materializer import PromptMaterializer
from zenml.prompts.prompt import Prompt


def test_prompt_materializer_basic(clean_client):
    """Test the PromptMaterializer with a basic prompt."""

    prompt = Prompt(
        template="Hello, {name}! How are you today?",
        variables={"name": "Alice"},
        description="A simple greeting prompt",
        task_type="conversation",
        model_type="gpt-4",
    )

    _test_materializer(
        step_output=prompt,
        materializer_class=PromptMaterializer,
        assert_visualization_exists=True,
    )


def test_prompt_materializer_no_variables(clean_client):
    """Test the PromptMaterializer with a prompt that has no variables."""

    prompt = Prompt(
        template="This is a static prompt with no variables.",
        description="A static prompt for testing",
    )

    _test_materializer(
        step_output=prompt,
        materializer_class=PromptMaterializer,
        assert_visualization_exists=True,
    )


def test_prompt_materializer_complex(clean_client):
    """Test the PromptMaterializer with a complex prompt."""

    prompt = Prompt(
        template="You are a {role} assistant. Please {task} the following text: {text}",
        variables={
            "role": "helpful",
            "task": "summarize",
            "text": "This is some sample text to process.",
        },
        metadata={"version": "1.0", "author": "test_user", "language": "en"},
        description="A complex multi-variable prompt for text processing",
        task_type="text_processing",
        model_type="gpt-4",
        created_at=datetime.now(),
    )

    _test_materializer(
        step_output=prompt,
        materializer_class=PromptMaterializer,
        assert_visualization_exists=True,
    )


def test_prompt_format_method():
    """Test the Prompt format method."""

    prompt = Prompt(
        template="Hello, {name}! Your score is {score}.",
        variables={"name": "Bob", "score": 95},
    )

    # Test with default variables
    formatted = prompt.format()
    assert formatted == "Hello, Bob! Your score is 95."

    # Test with override variables
    formatted = prompt.format(name="Charlie", score=87)
    assert formatted == "Hello, Charlie! Your score is 87."

    # Test with partial override
    formatted = prompt.format(score=100)
    assert formatted == "Hello, Bob! Your score is 100."


def test_prompt_get_variable_names():
    """Test the get_variable_names method."""

    prompt = Prompt(
        template="Hello {name}, today is {day} and the weather is {weather}."
    )

    variable_names = prompt.get_variable_names()
    assert set(variable_names) == {"name", "day", "weather"}


def test_prompt_validate_variables():
    """Test the validate_variables method."""

    # Test with complete variables
    prompt = Prompt(
        template="Hello {name}, your age is {age}.",
        variables={"name": "Alice", "age": 30},
    )
    assert prompt.validate_variables() is True

    # Test with incomplete variables
    prompt = Prompt(
        template="Hello {name}, your age is {age}.",
        variables={"name": "Alice"},  # missing 'age'
    )
    assert prompt.validate_variables() is False

    # Test with no variables needed
    prompt = Prompt(template="This has no variables.")
    assert prompt.validate_variables() is True


def test_prompt_to_dict_from_dict():
    """Test the to_dict and from_dict methods."""

    original_prompt = Prompt(
        template="Hello {name}!",
        variables={"name": "Test"},
        description="Test prompt",
        task_type="greeting",
    )

    # Convert to dict
    prompt_dict = original_prompt.to_dict()

    # Convert back to Prompt
    restored_prompt = Prompt.from_dict(prompt_dict)

    # Check they are equivalent
    assert restored_prompt.template == original_prompt.template
    assert restored_prompt.variables == original_prompt.variables
    assert restored_prompt.description == original_prompt.description
    assert restored_prompt.task_type == original_prompt.task_type
