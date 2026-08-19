#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Unit tests for OAuthDeviceSchema.internal_update."""

from uuid import uuid4

from zenml.enums import OAuthDeviceStatus
from zenml.models import (
    OAuthDeviceInternalRequest,
    OAuthDeviceInternalUpdate,
)
from zenml.zen_stores.schemas.device_schemas import OAuthDeviceSchema


def _new_device() -> OAuthDeviceSchema:
    schema, _, _ = OAuthDeviceSchema.from_request(
        OAuthDeviceInternalRequest(client_id=uuid4(), expires_in=600)
    )
    return schema


def test_internal_update_clears_user_id_when_requested() -> None:
    """Test that clear_user_id detaches a device from its previous owner.

    A device reused for a new authorization attempt must lose its
    previous owner, otherwise verification as a different user is rejected
    as belonging to someone else.
    """
    device = _new_device()
    device.user_id = uuid4()

    device.internal_update(
        OAuthDeviceInternalUpdate(
            status=OAuthDeviceStatus.PENDING,
            clear_user_id=True,
        )
    )

    assert device.user_id is None
    assert device.status == OAuthDeviceStatus.PENDING.value


def test_internal_update_leaves_user_id_untouched_by_default() -> None:
    """Test that a plain update leaves an existing user_id untouched.

    Without clear_user_id, an existing user association must survive an
    update -- e.g. the verification step that only changes status/attempt
    counters shouldn't accidentally detach the device from its owner.
    """
    device = _new_device()
    owner_id = uuid4()
    device.user_id = owner_id

    device.internal_update(OAuthDeviceInternalUpdate(failed_auth_attempts=1))

    assert device.user_id == owner_id


def test_internal_update_sets_user_id_on_verification() -> None:
    """Test that normal verification still sets user_id as before.

    Verifying a pending device assigns it to the verifying user, the
    normal (non-reuse) path this fix must not disturb.
    """
    device = _new_device()
    assert device.user_id is None

    new_owner = uuid4()
    device.internal_update(
        OAuthDeviceInternalUpdate(
            status=OAuthDeviceStatus.VERIFIED,
            user_id=new_owner,
        )
    )

    assert device.user_id == new_owner
