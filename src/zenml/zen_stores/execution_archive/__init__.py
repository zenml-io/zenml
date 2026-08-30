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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Archiving of execution history out of the SQL database.

Modules, in the order an archive moves through them:

- `capture`: reads one execution family and its closure evidence from SQL;
- `codec`, `models`, `payload`: canonical encoding, object references and
  the manifest and payload formats;
- `storage`, `targets`: content-addressed object storage over any artifact
  store implementation, and the configured target it writes to;
- `catalog`: the `execution_archive` rows and every state transition;
- `eligibility`: the gates a family must pass;
- `archiver`, `compactor`: export and verification of the copy, the
  authority switch, compaction and restore;
- `maintenance`: bounded preview and apply passes over a project;
- `cache`, `hydrator`: serving archived payload to readers once an archive
  is authoritative for its rows.
"""
