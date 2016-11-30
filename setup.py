# -*- encoding: utf8 -*-
import glob
import io
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ).read()


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        errno = tox.cmdline(args=shlex.split(self.tox_args))
        sys.exit(errno)


setup(
    name="forklift",
    version="3.3.8",
    license="MIT",
    description="CLI tool for managing automated tasks.",
    long_description="",
    author="Steve Gourley",
    author_email="SGourley@utah.gov",
    url="https://github.com/agrc/forklift",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(i))[0] for i in glob.glob("src/*.py")],
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
        "Programming Language :: Python :: 2.7",
        "Topic :: Utilities",
    ],
    keywords=[
    ],
    install_requires=[
        'docopt==0.6.2',
        'pystache==0.5.4',
        'colorama==0.3.7',
        'gitpython==2.0.4',
        'requests==2.10.0',
        #: pyopenssl, ndg-httpsclient, pyasn1 are there to disable ssl warnings in requests
        'pyopenssl>=16.0.0',
        'ndg-httpsclient==0.4.0',
        'pyasn1==0.1.9',
        'faulthandler==2.4.0'
    ],
    dependency_links=[
    ],
    extras_require={
    },
    entry_points={
        "console_scripts": [
            "forklift = forklift.__main__:main"
        ]
    },
    cmdclass={
        'test': Tox
    },
    tests_require=[
        'tox'
    ],
)
