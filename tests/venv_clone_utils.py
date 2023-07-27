# Copyright (c) 2011, Edward George, based on code contained within the
# virtualenv workspace.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""The below code is copied from the virtualenv-clone source repo with minor
changes to make it work for the specific usecase of zenml. All credits go to
https://github.com/edwardgeorge for the core implementation.
"""

import itertools
import os.path
import re
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

from zenml.logger import get_logger

logger = get_logger(__name__)

env_bin_dir = "bin"
if sys.platform == "win32":
    env_bin_dir = "Scripts"

python_exe = "python"
if sys.platform == "win32":
    python_exe = "python.exe"


class UserError(Exception):
    pass


def _dirmatch(path: str, matchwith: str) -> bool:
    """Check if path is within matchwith's tree.

    Args:
        path: Path to be checked
        matchwith: Path to be matched with

    Returns:
        Boolean, true if matched, false else
    >>> _dirmatch('/home/foo/bar', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar/', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar/etc', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar2', '/home/foo/bar')
    False
    >>> _dirmatch('/home/foo/bar2/etc', '/home/foo/bar')
    False
    """
    matchlen = len(matchwith)
    return bool(path.startswith(matchwith) and path[matchlen: matchlen + 1] in [os.sep, "",])


def _virtualenv_sys(venv_path: str) -> Tuple[str, list]:
    """Obtain python version and path info from a virtualenv.

    Args:
        venv_path: Location of the virtual environment

    Returns:
        tuple with two entries, python version and a list of paths in the
        sys path of the virtual environment
    """
    executable = os.path.join(venv_path, env_bin_dir, "python")
    # Must use "executable" as the first argument rather than as the
    # keyword argument "executable" to get correct value from sys.path
    p = subprocess.Popen(
        [
            executable,
            "-c",
            "import sys;"
            'print ("%d.%d" % (sys.version_info.major,'
            " sys.version_info.minor));"
            'print ("\\n".join(sys.path));',
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
    )
    stdout, err = p.communicate()
    assert not p.returncode and stdout
    lines = stdout.decode("utf-8").splitlines()
    return lines[0], list(filter(bool, lines[1:]))


def clone_virtualenv(src_dir: str, dst_dir: str) -> None:
    """Clone virtual environment from src_dir into new dst_dir.

    Args:
        src_dir: Source directory of the original virtual environment
        dst_dir: Destination directory where it should be cloned to
    """
    src_dir = os.path.realpath(src_dir)
    dst_dir = os.path.realpath(dst_dir)
    if not os.path.exists(src_dir):
        raise UserError("src dir %r does not exist" % src_dir)
    if os.path.exists(dst_dir):
        raise UserError("dest dir %r exists" % dst_dir)

    logger.info("Cloning virtualenv '%s' => '%s'..." % (src_dir, dst_dir))
    shutil.copytree(
        src_dir, dst_dir, symlinks=True, ignore=shutil.ignore_patterns("*.pyc")
    )
    version, sys_path = _virtualenv_sys(dst_dir)
    logger.info("Fixing scripts in bin...")
    fixup_scripts(src_dir, dst_dir, version)

    if old_path_in_sys_path(sys_path, src_dir):
        # only need to fix stuff in sys.path if we have old
        # paths in the sys.path of new python env. right?
        logger.info("Fixing paths in sys.path...")
        fixup_syspath_items(sys_path, src_dir, dst_dir)
    v_sys = _virtualenv_sys(dst_dir)
    remaining = old_path_in_sys_path(v_sys[1], src_dir)
    assert not remaining, v_sys
    fix_symlink_if_necessary(src_dir, dst_dir)


def old_path_in_sys_path(sys_path: List[str], src_dir: str) -> bool:
    """Checks if sys path contains reference to the old venv.

    Args:
        sys_path: Contents of the sys path as list
        src_dir: Path to the old virtualenv
    """
    return any(i for i in sys_path if _dirmatch(i, src_dir))


def fix_symlink_if_necessary(src_dir: str, dst_dir: str) -> None:
    """Sometimes the source virtual environment has symlinks that point to
    itself. One example is $OLD_VIRTUAL_ENV/local/lib points to
    $OLD_VIRTUAL_ENV/lib. This function makes sure $NEW_VIRTUAL_ENV/local/lib
    will point to $NEW_VIRTUAL_ENV/lib. Usually this goes unnoticed unless one
    tries to upgrade a package though pip, so this bug would be hard to find.

    Args:
        src_dir: Source directory of the original virtual environment
        dst_dir: Destination directory where it should be cloned to
    """
    logger.info(
        "Scanning for internal symlinks that point to the original virtual env."
    )
    for dirpath, dirnames, filenames in os.walk(dst_dir):
        for a_file in itertools.chain(filenames, dirnames):
            full_file_path = os.path.join(dirpath, a_file)
            if os.path.islink(full_file_path):
                target = os.path.realpath(full_file_path)
                if target.startswith(src_dir):
                    new_target = target.replace(src_dir, dst_dir)
                    logger.debug("Fixing symlink in %s" % (full_file_path,))
                    os.remove(full_file_path)
                    os.symlink(new_target, full_file_path)


def fixup_scripts(
    old_dir: str, new_dir: str, version: str, rewrite_env_python: bool = False
) -> None:
    """Fix paths and links within files of the environments so that
    they point at the right locations.

    Args:
        old_dir: Source directory where original virtual environment resides
        new_dir: New location of the virtual environment
        version: Python version associated with the venv
        rewrite_env_python: Boolean to declare if standard python env
            shebang like `#!/usr/bin/env python` should be rewritten to point at
            the python executable of the new virtual environment
    """
    bin_dir = os.path.join(new_dir, env_bin_dir)
    root, dirs, files = next(os.walk(bin_dir))
    pybinre = re.compile(r"pythonw?([0-9]+(\.[0-9]+(\.[0-9]+)?)?)?$")
    for file_ in files:
        filename = os.path.join(root, file_)
        if file_ in ["python", f"python{version}", "activate_this.py"]:
            continue
        elif file_.startswith("python") and pybinre.match(file_):
            # ignore other possible python binaries
            continue
        elif file_.endswith(".pyc"):
            # ignore compiled files
            continue
        elif file_ == "activate" or file_.startswith("activate."):
            fixup_activate(os.path.join(root, file_), old_dir, new_dir)
        elif os.path.islink(filename):
            fixup_link(filename, old_dir, new_dir)
        elif os.path.isfile(filename):
            fixup_script_(
                root,
                file_,
                old_dir,
                new_dir,
                version,
                rewrite_env_python=rewrite_env_python,
            )


def fixup_script_(
    root: str,
    file_: str,
    old_dir: str,
    new_dir: str,
    py_version: str,
    rewrite_env_python: bool = False,
) -> None:
    """This is meant to rewrite the shebang of files in the destination
    venv that still point at the python executable of the original venv
    or even the system python executable.

    Args:
        root: Directory root of the file
        file_: Filename
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
        py_version: Python version
        rewrite_env_python: Boolean to declare if standard python env
            shebang like `#!/usr/bin/env python` should be rewritten to point at
            the python executable of the new virtual environment
    """
    old_shebang = (
        f"#!{os.path.abspath(old_dir)}{os.sep}{env_bin_dir}"
        f"{os.sep}{python_exe}"
    )
    new_shebang = (
        f"#!{os.path.abspath(new_dir)}{os.sep}{env_bin_dir}"
        f"{os.sep}{python_exe}"
    )
    env_shebang = "#!/usr/bin/env python"

    filename = os.path.join(root, file_)
    with open(filename, "rb") as f:
        if f.read(2) != b"#!":
            # no shebang
            return
        f.seek(0)
        lines = f.readlines()

    if not lines:
        # warn: empty script
        return

    def rewrite_shebang(python_version: Optional[str] = None):
        """Overwrite shebang of a given file with new_shebang.

        Args:
            python_version: Python version
        """
        logger.debug("Fixing shebang within %s" % filename)
        shebang = new_shebang
        if python_version:
            shebang = shebang + python_version
        shebang = (shebang + "\n").encode("utf-8")
        with open(filename, "wb") as f:
            f.write(shebang)
            f.writelines(lines[1:])

    try:
        bang = lines[0].decode("utf-8").strip()
    except UnicodeDecodeError:
        # binary file
        return

    # This takes care of the scheme in which shebang is of type
    # '#!/venv/bin/python3' while the version of system python
    # is of type 3.x e.g. 3.5.
    short_version = bang[len(old_shebang):]

    if not bang.startswith("#!"):
        return
    elif bang == old_shebang:
        rewrite_shebang()
    elif (
        bang.startswith(old_shebang) and bang[len(old_shebang):] == py_version
    ):
        rewrite_shebang(py_version)
    elif (
        bang.startswith(old_shebang)
        and short_version
        and bang[len(old_shebang):] == short_version
    ):
        rewrite_shebang(short_version)
    elif rewrite_env_python and bang.startswith(env_shebang):
        if bang == env_shebang:
            rewrite_shebang()
        elif bang[len(env_shebang):] == py_version:
            rewrite_shebang(py_version)
    else:
        # Nothing to do here
        return


def fixup_activate(filename: str, old_dir: str, new_dir: str) -> None:
    """Within activate file, replace all mentions of the old venv with the path
    of the new venv.

    Args:
        filename: Name of the file
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
    """
    logger.debug("Replacing links in %s" % filename)
    with open(filename, "rb") as f:
        data = f.read().decode("utf-8")

    data = data.replace(old_dir, new_dir)
    with open(filename, "wb") as f:
        f.write(data.encode("utf-8"))


def fixup_link(
    filename: str, old_dir: str, new_dir: str, target: Optional[str] = None
) -> None:
    """Within a given file, replace all mentions of the old venv with the path
    of the new venv.

    Args:
        filename: Name of the file
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
        target: ???
    """
    logger.debug("Replacing links in %s" % filename)
    if target is None:
        target = os.readlink(filename)

    origdir = os.path.dirname(os.path.abspath(filename)).replace(
        new_dir, old_dir
    )
    if not os.path.isabs(target):
        target = os.path.abspath(os.path.join(origdir, target))
        rellink = True
    else:
        rellink = False

    if _dirmatch(target, old_dir):
        if rellink:
            # keep relative links, but don't keep original in case it
            # traversed up out of, then back into the venv.
            # so, recreate a relative link from absolute.
            target = target[len(origdir):].lstrip(os.sep)
        else:
            target = target.replace(old_dir, new_dir, 1)

    # else: links outside the venv, replaced with absolute path to target.
    _replace_symlink(filename, target)


def _replace_symlink(filename: str, newtarget: str) -> None:
    """Replace any symlinks with absolute path target.

    Args:
        filename: Name of the file
        newtarget: Symlink target
    """
    logger.debug("Replacing links outside of path for %s" % filename)

    tmpfn = "%s.new" % filename
    os.symlink(newtarget, tmpfn)
    try:
        shutil.move(tmpfn, filename)
    except OSError:
        os.remove(filename)
        shutil.move(tmpfn, filename)


def fixup_syspath_items(
    syspath: List[str], old_dir: str, new_dir: str
) -> None:
    """Replace mentions of the old venv in sys path with the new venv.

    Args:
        syspath: List of paths in sys path
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
    """
    for path in syspath:
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if _dirmatch(path, old_dir):
            path = path.replace(old_dir, new_dir, 1)
            if not os.path.exists(path):
                continue
        elif not _dirmatch(path, new_dir):
            continue
        root, dirs, files = next(os.walk(path))
        for file_ in files:
            filename = os.path.join(root, file_)
            if filename.endswith(".pth"):
                fixup_pth_file(filename, old_dir, new_dir)
            elif filename.endswith(".egg-link"):
                fixup_egglink_file(filename, old_dir, new_dir)


def fixup_pth_file(filename: str, old_dir: str, new_dir: str) -> None:
    """Within a given file, replace all mentions of the old venv with the path
    of the new venv.

    Args:
        filename: Name of the file
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
    """
    logger.debug("Replacing paths within .pth file: %s" % filename)

    with open(filename, "r") as f:
        lines = f.readlines()

    has_change = False

    for num, line in enumerate(lines):
        line = (
            line.decode("utf-8") if hasattr(line, "decode") else line
        ).strip()

        if not line or line.startswith("#") or line.startswith("import "):
            continue
        elif _dirmatch(line, old_dir):
            lines[num] = line.replace(old_dir, new_dir, 1)
            has_change = True

    if has_change:
        with open(filename, "w") as f:
            payload = (
                os.linesep.join([line.strip() for line in lines]) + os.linesep
            )
            f.write(payload)


def fixup_egglink_file(filename: str, old_dir: str, new_dir: str) -> None:
    """Within a given file, replace all mentions of the old venv with the path
    of the new venv.

    Args:
        filename: Name of the file
        old_dir: Directory location of the old virtual environment
        new_dir: Directory location of the new virtual environment
    """
    logger.debug("Replacing paths within .egg-link file: %s" % filename)
    with open(filename, "rb") as f:
        link = f.read().decode("utf-8").strip()
    if _dirmatch(link, old_dir):
        link = link.replace(old_dir, new_dir, 1)
        with open(filename, "wb") as f:
            link = (link + "\n").encode("utf-8")
            f.write(link)
