# Copyright 2021 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module for input resolution exceptions.

Theses exceptions can be raised from ResolverStartegy or ResolverOp
implementation, and each exception is specially handled in input resolution
process. Other errors raised during the input resolution will not be catched
and be propagated to the input resolution caller.
"""
import grpc

# Disable lint errors that enforces all exception name to end with -Error.
# pylint: disable=g-bad-exception-name


class InputResolutionError(Exception):
  """Base exception class for input resolution related errors."""
  grpc_code = grpc.StatusCode.UNKNOWN

  @property
  def grpc_code_value(self) -> int:
    return self.grpc_code.value[0]


class InvalidArgument(InputResolutionError):
  """When user provided value is invalid."""
  grpc_code = grpc.StatusCode.INVALID_ARGUMENT


class FailedPreconditionError(InputResolutionError):
  """When the precondition is not met."""
  grpc_code = grpc.StatusCode.FAILED_PRECONDITION


class InternalError(InputResolutionError):
  """For TFX internal errors."""
  grpc_code = grpc.StatusCode.INTERNAL


class InputResolutionSignal(Exception):
  """Base exception class for non-error input resolution signals."""


class SkipSignal(InputResolutionSignal):
  """Special signal to resolve empty input resolution result.

  Normally empty input resolution result is regarded as an error (in synchronous
  pipeline). Raising SkipSignal would resolve empty list input without an error.

  TFX Conditional uses SkipSignal to _not_ execute components if the branch
  predicate evaluates to false.
  """
