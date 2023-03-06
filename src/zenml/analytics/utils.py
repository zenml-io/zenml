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
import logging
import numbers
from datetime import date, datetime
from decimal import Decimal
import json
from uuid import UUID
import six

logger = logging.getLogger(__name__)


def clean(item):
    if isinstance(item, Decimal):
        return float(item)
    elif isinstance(
        item,
        (six.string_types, bool, numbers.Number, datetime, date, type(None)),
    ):
        return item
    elif isinstance(item, (set, list, tuple)):
        return _clean_list(item)
    elif isinstance(item, dict):
        return _clean_dict(item)
    else:
        return _coerce_unicode(item)


def _clean_list(list_):
    return [clean(item) for item in list_]


def _clean_dict(dict_):
    data = {}
    for k, v in six.iteritems(dict_):
        try:
            data[k] = clean(v)
        except TypeError:
            logger.warning(
                "Dictionary values must be serializeable to "
                'JSON "%s" value %s of type %s is unsupported.',
                k,
                v,
                type(v),
            )
    return data


def _coerce_unicode(cmplx):
    try:
        item = cmplx.decode("utf-8", "strict")
    except AttributeError as exception:
        item = ":".join(exception)
        item.decode("utf-8", "strict")
        logger.warning("Error decoding: %s", item)
        return None
    return item


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)
