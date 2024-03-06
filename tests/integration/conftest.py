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

from unittest.mock import MagicMock

import pytest
from requests import patch

from tests.harness.utils import TheZenRemembers


@pytest.fixture(scope="function", autouse=True)
def patch_client():
    # @cache
    # def get_patch_paths() -> List[str]:
    #     client_import = "from zenml.client import Client"
    #     to_patch = ["zenml.client.Client"]
    #     python_indenter = "    "
    #     for root, _, files in os.walk("src"):
    #         for file in files:
    #             if file.endswith(".py") and file != "__init__.py":
    #                 with open(os.path.join(root, file), "r") as f:
    #                     source_code = f.read()
    #                     if client_import in source_code:
    #                         # current_ident = 0
    #                         code_stack = []
    #                         lib_path_without_src = root.split(os.sep)[1:]
    #                         filename_without_ext = file[:-3]
    #                         patch_prefix = lib_path_without_src + [
    #                             filename_without_ext
    #                         ]
    #                         # multiline_comment = False
    #                         source_code = [
    #                             l for l in source_code.splitlines() if l
    #                         ]
    #                         for i, line in enumerate(source_code):
    #                             if client_import == line.strip():
    #                                 code_stack = {}
    #                                 for prev_line in source_code[:i][::-1]:
    #                                     if 0 in code_stack:
    #                                         break
    #                                     ident = (
    #                                         prev_line.count(python_indenter)
    #                                         if prev_line.startswith(
    #                                             python_indenter
    #                                         )
    #                                         else 0
    #                                     )
    #                                     if ident in code_stack:
    #                                         continue
    #                                     if prev_line.strip().startswith(
    #                                         "class "
    #                                     ) or prev_line.strip().startswith(
    #                                         "def "
    #                                     ):
    #                                         class_pos = prev_line.find(
    #                                             "class "
    #                                         )
    #                                         def_pos = prev_line.find("def ")
    #                                         stack_name = prev_line[
    #                                             def_pos + len("def ")
    #                                             if def_pos > class_pos
    #                                             else class_pos
    #                                             + len("class ") :
    #                                         ]
    #                                         bracket_pos = stack_name.find("(")
    #                                         colon_pos = stack_name.find(":")
    #                                         if (
    #                                             bracket_pos > 0
    #                                             and bracket_pos < colon_pos
    #                                         ):
    #                                             stack_name = stack_name[
    #                                                 :bracket_pos
    #                                             ]
    #                                         else:
    #                                             stack_name = stack_name[
    #                                                 :colon_pos
    #                                             ]
    #                                         code_stack[ident] = stack_name
    #                                 to_patch.append(
    #                                     ".".join(
    #                                         patch_prefix
    #                                         + [
    #                                             code_stack[k]
    #                                             for k in sorted(
    #                                                 code_stack.keys()
    #                                             )
    #                                         ]
    #                                         + ["Client"]
    #                                     )
    #                                 )

    #                             # if not line:
    #                             #     continue
    #                             # if line.count('"""') == 1:
    #                             #     multiline_comment = not multiline_comment
    #                             # if not multiline_comment:
    #                             #     ident = (
    #                             #         line.count(python_indenter)
    #                             #         if line.startswith(python_indenter)
    #                             #         else 0
    #                             #     )
    #                             #     if ident > current_ident:
    #                             #         current_ident += 1
    #                             #     if ident < current_ident:
    #                             #         current_ident -= 1
    #                             #         if code_stack:
    #                             #             code_stack.pop()
    #                             #     if "class " in line or "def " in line:
    #                             #         class_pos = line.find("class ")
    #                             #         def_pos = line.find("def ")
    #                             #         stack_name = line[
    #                             #             def_pos + len("def ")
    #                             #             if def_pos > class_pos
    #                             #             else class_pos + len("class ") :
    #                             #         ]
    #                             #         bracket_pos = stack_name.find("(")
    #                             #         colon_pos = stack_name.find(":")
    #                             #         if (
    #                             #             bracket_pos > 0
    #                             #             and bracket_pos < colon_pos
    #                             #         ):
    #                             #             stack_name = stack_name[
    #                             #                 :bracket_pos
    #                             #             ]
    #                             #         else:
    #                             #             stack_name = stack_name[:colon_pos]
    #                             #         code_stack.append(stack_name)
    #                             #     if client_import in line:
    #                             #         to_patch.append(
    #                             #             ".".join(
    #                             #                 patch_prefix
    #                             #                 + code_stack
    #                             #                 + ["Client"]
    #                             #             )
    #                             #         )

    #     return to_patch

    # patch_paths = get_patch_paths()
    # patchers: List[_patch[TheZenRemembers]] = []
    # for each in patch_paths:
    #     patcher = patch(each, TheZenRemembers)
    #     try:
    #         patcher.start()
    #     except AttributeError:
    #         print("__NOT_PATCHED__", each)
    #         pass
    #     else:
    #         patchers.append(patcher)
    # try:
    #     yield
    # finally:
    #     for patcher in patchers:
    #         patcher.stop()
    _module = MagicMock(name="zenml_client_mock")
    _module.Client.return_value = TheZenRemembers
    with patch.dict("sys.modules", {"zenml.client": _module}):
        yield
