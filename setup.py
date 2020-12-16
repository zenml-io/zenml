#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is used to create the package we'll publish to PyPI.

.. currentmodule:: setup.py
.. moduleauthor:: maiot GmbH <support@maiot.io>
"""

import importlib.util
import os
from codecs import open  # Use a consistent encoding.
from os import path
from pathlib import Path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the base version from the library.  (We'll find it in the `version.py`
# file in the src directory, but we'll bypass actually loading up the library.)
vspec = importlib.util.spec_from_file_location(
    "version",
    str(Path(__file__).resolve().parent /
        'zenml' / 'utils' / "version.py")
)
vmod = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(vmod)
version = getattr(vmod, '__version__')

# If the environment has a build number set...
if os.getenv('buildnum') is not None:
    # ...append it to the version.
    version = "{version}.{buildnum}".format(
        version=version,
        buildnum=os.getenv('buildnum')
    )

setup(
    name='zenml',
    description="ZenML: Write production-ready ML code.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples",
                 "docs"]),
    version=version,
    install_requires=[
        "pip-check-reqs>=2.0.1,<3",
        "click>=7.0,<8",
        "setuptools>=38.4.0",
        "nbformat>=5.0.4",
        "panel==0.8.3",
        "plotly==4.0.0",
        "tabulate==0.8.7",
        "numpy==1.18.0",
        "httplib2==0.17.0",
        "tfx==0.25.0",
        "fire==0.3.1",
        "gitpython==3.1.11",
        "analytics-python==1.2.9",
        "distro==1.5.0"
    ],
    entry_points="""
    [console_scripts]
    zenml=zenml.cli.cli:cli
    """,
    python_requires=">=3.6.*",
    license='Apache License 2.0',  # noqa
    author='maiot GmbH',
    author_email='support@maiot.io',
    url='https://docs.zenml.io/',
    keywords=[
        "deep", "learning", "production", "machine", "pipeline", "mlops"
    ],
    # See https://PyPI.python.org/PyPI?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for.
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        # Pick your license.  (It should match "license" above.)

        'License :: OSI Approved :: Apache Software License',  # noqa
        # noqa
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.6',
    ],
    include_package_data=True
)
