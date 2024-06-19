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
"""Endpoint definitions for tags."""

from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    REPORTS,
    VERSION_1,
)
from zenml.models import (
    Page,
    ReportRequest,
    ReportResponse,
    ReportUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    zen_store,
)

#########
# Reports
#########

router = APIRouter(
    prefix=API + VERSION_1 + REPORTS,
    tags=["reports"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_report(
    report: ReportRequest,
    _: AuthContext = Security(authorize),
) -> ReportResponse:
    return zen_store().create_report(report)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_reports(
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ReportResponse]:
    return zen_store().list_reports(hydrate=hydrate)


@router.get(
    "/{report_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_report(
    report_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ReportResponse:
    return zen_store().get_report(report_id=report_id, hydrate=hydrate)


@router.put(
    "/{report_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_report(
    report_id: UUID,
    report_update: ReportUpdate,
    _: AuthContext = Security(authorize),
) -> ReportResponse:
    return zen_store().update_report(
        report_id=report_id, report_update_model=report_update
    )


@router.delete(
    "/{report_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_report(
    report_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    zen_store().delete_report(report_id)
