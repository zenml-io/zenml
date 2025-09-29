#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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


import re
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors import AWSDeployerFlavor
from zenml.integrations.aws.flavors.aws_deployer_flavor import (
    DEFAULT_RESOURCE_COMBINATIONS,
)


def test_aws_app_runner_deployer_flavor_attributes():
    """Tests that the basic attributes of the AWS App Runner deployer flavor are set correctly."""
    flavor = AWSDeployerFlavor()
    assert flavor.type == StackComponentType.DEPLOYER
    assert flavor.name == "aws"


DG_URL = "https://docs.aws.amazon.com/apprunner/latest/dg/architecture.html"  # table with exact valid pairs


def _fetch_documented_supported_resource_combinations(
    html: str,
) -> List[Tuple[float, float]]:
    """Parse the 'App Runner supported configurations' table into (vCPU, GB) pairs."""
    soup = BeautifulSoup(html, "html.parser")
    # Find the section that contains the supported configurations table
    # Strategy: locate the heading text, then the first following table
    heading = None
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if "supported configurations" in tag.get_text(strip=True).lower():
            heading = tag
            break
    if not heading:
        raise RuntimeError("Supported configurations heading not found")

    table = heading.find_next("table")
    if not table:
        raise RuntimeError("Supported configurations table not found")

    rows = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) != 2:  # Expect 2 columns: CPU | Memory
            continue
        if cells[0].lower().startswith("cpu"):  # skip header row
            continue
        cpu = _to_vcpu(cells[0])
        mem = _to_gb(cells[1])
        if cpu is not None and mem is not None:
            rows.append((cpu, mem))

    if not rows:
        raise RuntimeError("No (CPU, Memory) pairs parsed from table")
    # Deduplicate and sort
    return sorted(set(rows), key=lambda x: (x[0], x[1]))


def _to_vcpu(s: str) -> Optional[float]:
    m = re.search(r"([\d.]+)\s*v?CPU", s, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _to_gb(s: str) -> Optional[float]:
    # Accept MB/GB but App Runner uses GB in the table
    m = re.search(r"([\d.]+)\s*GB", s, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*MB", s, re.IGNORECASE)
    return (float(m.group(1)) / 1024.0) if m else None


def test_aws_app_runner_deployer_flavor_resource_combinations():
    """Tests that the resource combinations of the AWS App Runner deployer flavor are set correctly."""
    dg_html = requests.get(DG_URL, timeout=15).text
    supported_combinations = _fetch_documented_supported_resource_combinations(
        dg_html
    )
    # If this test fails, it is likely because the default resource combinations in the
    # AWS App Runner deployer flavor are no longer up to date and need to be
    # updated to match
    assert DEFAULT_RESOURCE_COMBINATIONS == supported_combinations
