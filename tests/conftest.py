#!/usr/bin/env python
# * coding: utf8 *
'''
conftest.py

Sets up testing environment
'''
from os import path, remove

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
