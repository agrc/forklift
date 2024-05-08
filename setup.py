#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
setup.py
A module that installs forklift
"""

import glob
from os.path import basename, splitext
from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="forklift",
    version="1.0.0",
    license="MIT",
    description="CLI tool for managing automated tasks.",
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="UGRC",
    author_email="ugrc-developers@utah.gov",
    url="https://github.com/agrc/forklift",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(i))[0] for i in glob.glob("src/*.py")],
    python_requires=">=3",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
    project_urls={
        "Issue Tracker": "https://github.com/agrc/forklift/issues",
    },
    keywords=[],
    install_requires=[
        "arcgis",
        "colorama==0.*",
        "docopt==0.6.*",
        "gitpython==3.*",
        "ndg-httpsclient==0.*",
        "pyasn1==0.*",
        "pyopenssl==23.*",
        "pystache==0.*",
        "requests==2.*",
        "sendgrid==6.*",
        "xxhash==2.*",
        #: pyopenssl, ndg-httpsclient, pyasn1 are there to disable ssl warnings in requests
    ],
    extras_require={
        "tests": [
            "pytest-cov==5.*",
            "pytest-instafail==0.5.*",
            "pytest-mock==3.*",
            "pytest-ruff==0.*",
            "pytest-watch==4.*",
            "pytest==8.*",
            "ruff==0.*",
        ]
    },
    setup_requires=["pytest-runner"],
    entry_points={"console_scripts": ["forklift = forklift.__main__:main"]},
)
