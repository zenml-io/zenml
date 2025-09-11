#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Pure unit tests for serving app functions."""

from zenml.deployers.serving.app import (
    PipelineInvokeRequest,
    _json_type_matches,
    _validate_request_parameters,
)


class TestPipelineInvokeRequest:
    """Unit tests for PipelineInvokeRequest model."""

    def test_default_values(self):
        """Test default values for invoke request."""
        request = PipelineInvokeRequest()

        assert request.parameters == {}
        assert request.run_name is None
        assert request.timeout is None

    def test_with_values(self):
        """Test invoke request with values."""
        request = PipelineInvokeRequest(
            parameters={"city": "Paris"}, run_name="test_run", timeout=300
        )

        assert request.parameters == {"city": "Paris"}
        assert request.run_name == "test_run"
        assert request.timeout == 300

    def test_parameter_types(self):
        """Test parameter type validation."""
        # Valid parameters dict
        request = PipelineInvokeRequest(parameters={"key": "value"})
        assert isinstance(request.parameters, dict)

        # Empty parameters should be valid
        request = PipelineInvokeRequest(parameters={})
        assert request.parameters == {}

    def test_optional_fields(self):
        """Test optional field behavior."""
        # Only parameters provided
        request = PipelineInvokeRequest(parameters={"test": True})
        assert request.run_name is None
        assert request.timeout is None

        # All fields provided
        request = PipelineInvokeRequest(
            parameters={}, run_name="custom", timeout=600
        )
        assert request.run_name == "custom"
        assert request.timeout == 600


class TestJsonTypeMatching:
    """Unit tests for JSON type matching function."""

    def test_string_matching(self):
        """Test string type matching."""
        assert _json_type_matches("hello", "string") is True
        assert _json_type_matches("", "string") is True
        assert _json_type_matches(123, "string") is False
        assert _json_type_matches(True, "string") is False
        assert _json_type_matches([], "string") is False

    def test_integer_matching(self):
        """Test integer type matching."""
        assert _json_type_matches(42, "integer") is True
        assert _json_type_matches(0, "integer") is True
        assert _json_type_matches(-10, "integer") is True
        assert _json_type_matches(3.14, "integer") is False
        assert (
            _json_type_matches(True, "integer") is False
        )  # bool is not int in JSON schema
        assert _json_type_matches("123", "integer") is False

    def test_number_matching(self):
        """Test number type matching."""
        assert _json_type_matches(42, "number") is True
        assert _json_type_matches(3.14, "number") is True
        assert _json_type_matches(0, "number") is True
        assert _json_type_matches(-1.5, "number") is True
        assert (
            _json_type_matches(True, "number") is False
        )  # bool is not number in JSON schema
        assert _json_type_matches("42", "number") is False

    def test_boolean_matching(self):
        """Test boolean type matching."""
        assert _json_type_matches(True, "boolean") is True
        assert _json_type_matches(False, "boolean") is True
        assert _json_type_matches(1, "boolean") is False
        assert _json_type_matches(0, "boolean") is False
        assert _json_type_matches("true", "boolean") is False

    def test_array_matching(self):
        """Test array type matching."""
        assert _json_type_matches([1, 2, 3], "array") is True
        assert _json_type_matches([], "array") is True
        assert _json_type_matches(["a", "b"], "array") is True
        assert _json_type_matches("string", "array") is False
        assert _json_type_matches({"key": "value"}, "array") is False
        assert _json_type_matches(123, "array") is False

    def test_object_matching(self):
        """Test object type matching."""
        assert _json_type_matches({"key": "value"}, "object") is True
        assert _json_type_matches({}, "object") is True
        assert (
            _json_type_matches({"nested": {"object": True}}, "object") is True
        )
        assert _json_type_matches([1, 2], "object") is False
        assert _json_type_matches("string", "object") is False
        assert _json_type_matches(42, "object") is False

    def test_null_matching(self):
        """Test null type matching."""
        assert _json_type_matches(None, "null") is True
        assert _json_type_matches(0, "null") is False
        assert _json_type_matches("", "null") is False
        assert _json_type_matches(False, "null") is False

    def test_unknown_type(self):
        """Test unknown type returns False."""
        assert _json_type_matches("value", "unknown_type") is False
        assert _json_type_matches(123, "custom") is False


class TestRequestParameterValidation:
    """Unit tests for request parameter validation function."""

    def test_valid_parameters(self):
        """Test validation with valid parameters."""
        schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "count": {"type": "integer"},
                "active": {"type": "boolean"},
            },
            "required": ["city"],
        }

        params = {"city": "Paris", "count": 5, "active": True}
        result = _validate_request_parameters(params, schema)

        assert result is None  # No errors

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        }

        params = {}
        result = _validate_request_parameters(params, schema)

        assert result is not None
        assert "missing required fields: ['city']" in result

    def test_multiple_missing_required_fields(self):
        """Test validation with multiple missing required fields."""
        schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "country": {"type": "string"},
            },
            "required": ["city", "country"],
        }

        params = {}
        result = _validate_request_parameters(params, schema)

        assert result is not None
        assert "missing required fields:" in result
        assert "city" in result
        assert "country" in result

    def test_wrong_parameter_types(self):
        """Test validation with wrong parameter types."""
        schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "count": {"type": "integer"},
            },
        }

        params = {"city": "Paris", "count": "not_an_integer"}
        result = _validate_request_parameters(params, schema)

        assert result is not None
        assert "expected type integer" in result
        assert "count" in result

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        schema = {"type": "object", "properties": {"city": {"type": "string"}}}

        params = {"city": "Paris", "extra": "allowed"}
        result = _validate_request_parameters(params, schema)

        assert result is None  # Extra fields are allowed

    def test_non_dict_parameters(self):
        """Test validation with non-dict input."""
        schema = {"type": "object"}

        # String input
        result = _validate_request_parameters("not_a_dict", schema)
        assert result is not None
        assert "parameters must be an object" in result

        # List input
        result = _validate_request_parameters([1, 2, 3], schema)
        assert result is not None
        assert "parameters must be an object" in result

        # Number input
        result = _validate_request_parameters(123, schema)
        assert result is not None
        assert "parameters must be an object" in result

    def test_empty_schema(self):
        """Test validation with empty schema."""
        schema = {}
        params = {"any": "parameter"}

        result = _validate_request_parameters(params, schema)
        assert result is None  # Should pass with empty schema

    def test_none_schema(self):
        """Test validation with None schema."""
        schema = None
        params = {"any": "parameter"}

        result = _validate_request_parameters(params, schema)
        assert result is None  # Should pass with None schema

    def test_no_properties_in_schema(self):
        """Test validation with schema that has no properties."""
        schema = {"type": "object", "required": ["city"]}
        params = {"city": "Paris"}

        result = _validate_request_parameters(params, schema)
        assert (
            result is not None
        )  # Should fail because city is required but no properties defined

    def test_properties_without_type(self):
        """Test validation with properties that have no type specified."""
        schema = {
            "type": "object",
            "properties": {
                "city": {},  # No type specified
                "count": {"type": "integer"},
            },
        }

        params = {"city": "Paris", "count": 5}
        result = _validate_request_parameters(params, schema)

        assert result is None  # Should pass when no type is specified

    def test_boolean_edge_cases(self):
        """Test boolean type validation edge cases."""
        schema = {
            "type": "object",
            "properties": {"flag": {"type": "boolean"}},
        }

        # Valid booleans
        assert _validate_request_parameters({"flag": True}, schema) is None
        assert _validate_request_parameters({"flag": False}, schema) is None

        # Invalid booleans (in JSON schema, 1 and 0 are not booleans)
        result = _validate_request_parameters({"flag": 1}, schema)
        assert result is not None
        assert "expected type boolean" in result

        result = _validate_request_parameters({"flag": 0}, schema)
        assert result is not None
        assert "expected type boolean" in result

    def test_complex_nested_validation(self):
        """Test validation with complex nested structures."""
        schema = {
            "type": "object",
            "properties": {
                "user": {"type": "object"},
                "preferences": {"type": "array"},
                "metadata": {"type": "object"},
            },
            "required": ["user"],
        }

        # Valid complex parameters
        params = {
            "user": {"name": "John", "age": 30},
            "preferences": ["email", "sms"],
            "metadata": {"source": "api"},
        }
        result = _validate_request_parameters(params, schema)
        assert result is None

        # Invalid: user should be object, not string
        params = {
            "user": "john_doe",  # Should be object
            "preferences": ["email"],
        }
        result = _validate_request_parameters(params, schema)
        assert result is not None
        assert "expected type object" in result

    def test_validation_error_messages(self):
        """Test that error messages are clear and helpful."""
        schema = {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["temperature"],
        }

        # Test missing required field message
        result = _validate_request_parameters({}, schema)
        assert "missing required fields: ['temperature']" in result

        # Test type mismatch message
        result = _validate_request_parameters(
            {"temperature": "hot", "active": "yes"}, schema
        )
        assert result is not None
        # Should mention the first type error encountered
        assert (
            "temperature" in result and "expected type number" in result
        ) or ("active" in result and "expected type boolean" in result)
