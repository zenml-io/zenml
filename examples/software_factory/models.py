#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Structured data models for the software factory pipeline."""

from typing import List

from pydantic import BaseModel


class PRRef(BaseModel):
    """Pull request reference."""

    url: str
    number: int


class TestReport(BaseModel):
    """Test report."""

    passed: bool
    summary: str


class ReviewVerdict(BaseModel):
    """Review verdict."""

    approved: bool
    comments: List[str]


class Review(BaseModel):
    """Review."""

    approved: bool
    feedback: str = ""
