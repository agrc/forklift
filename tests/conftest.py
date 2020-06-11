#!/usr/bin/env python
# * coding: utf8 *
'''
conftest.py

Sets up testing environment
'''
from os import path, remove, sep, walk
from pathlib import Path
from shutil import copytree, rmtree
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from forklift import config

temp_config = path.join(path.abspath(path.dirname(__file__)), 'config.json')


@pytest.fixture(scope="session", autouse=True)
def setup():
    #: session set up
    config.config_location = temp_config
    config.create_default_config()

    yield

    #: session tear down
    if path.exists(config.config_location):
        remove(config.config_location)
        print('removed')


#: hook for making test result available in fixtures
#: ref: https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    #: when could be "setup", "call", or "teardown"
    setattr(item, f'{report.when}_report', report)


@pytest.fixture()
def test_gdb(request, tmp_path):
    #: get test name and directory and look for gdb or zip
    module = '/'.join(request.module.__name__.split('.')[1:])
    data_folder = Path(request.module.__file__).parent / 'data' / module
    test_name = request.function.__name__
    original_gdb = data_folder / f'{test_name}.gdb'
    original_zip = data_folder / f'{test_name}.zip'

    if original_gdb.exists():
        yield str(copytree(original_gdb, tmp_path / original_gdb.name))
    elif original_zip.exists():
        with ZipFile(original_zip) as zip_file:
            zip_file.extractall(tmp_path)
            yield str(tmp_path / f'{request.function.__name__}.gdb')
    else:
        raise MissingTestData(original_gdb, original_zip)

    #: Cleaning up tmp_path is not needed. Automatically cleaned up after a few runs
    #: ref: https://github.com/pytest-dev/pytest/issues/543

    if request.node.call_report.passed and original_gdb.exists():
        print('zipping up new gdb and removing it')
        #: if a .gdb was found but no .zip then zip it up and remove the original gdb
        zip_gdb(original_gdb, original_zip)
        rmtree(original_gdb)


def zip_gdb(source_gdb, destination_zip):
    #: zips up the source into the destination zip, overwriting any existing zip file
    with ZipFile(destination_zip, 'w', ZIP_DEFLATED) as zip_file:
        for root, dirs, files in walk(source_gdb):
            for file_name in files:
                if Path(file_name).suffix not in ['.lock']:
                    full_name = Path(root) / file_name
                    zip_file.write(full_name, Path(full_name.parent.name) / full_name.name)


class MissingTestData(Exception):
    '''raised when the test_gdb fixture can't find either a fgdb or zip file that matches the current test name
    '''

    def __init__(self, gdb_path, zip_path):
        self.gdb_path = gdb_path
        self.zip_path = zip_path
        self.message = f'Could not find {gdb_path} or {zip_path}!'
