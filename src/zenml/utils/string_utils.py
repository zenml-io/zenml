#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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


def get_human_readable_time(seconds: float) -> str:
    """Convert seconds into a human-readable string."""
    prefix = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    int_seconds = int(seconds)
    days, int_seconds = divmod(int_seconds, 86400)
    hours, int_seconds = divmod(int_seconds, 3600)
    minutes, int_seconds = divmod(int_seconds, 60)
    if days > 0:
        time_string = f"{days}d{hours}h{minutes}m{int_seconds}s"
    elif hours > 0:
        time_string = f"{hours}h{minutes}m{int_seconds}s"
    elif minutes > 0:
        time_string = f"{minutes}m{int_seconds}s"
    else:
        time_string = f"{seconds:.3f}s"

    return prefix + time_string


def get_human_readable_filesize(bytes_: int) -> str:
    """Convert a file size in bytes into a human-readable string."""
    size = abs(float(bytes_))
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if size < 1024.0 or unit == "GiB":
            break
        size /= 1024.0

    return f"{size:.2f} {unit}"
