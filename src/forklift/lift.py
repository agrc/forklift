#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import logging
import settings
from glob import glob
from json import dumps, loads
from os.path import abspath, exists

log = logging.getLogger(settings.LOGGER)


def init():
    if exists('config.json'):
        return 'config file already created.'

    default_plugin_locations = ['c:\\scheduled']

    log.debug('creating config.json file.')
    with open('config.json', 'w') as json_data_file:
        data = dumps(default_plugin_locations)

        log.debug('writing %s to %s', data, abspath(json_data_file.name))
        json_data_file.write(data)

        return abspath(json_data_file.name)


def list_plugins(paths=None):
    if paths is None:
        paths = _get_config_paths()

    return (location for location in _get_plugins_in_location(paths))


def _get_config_paths():
    if not exists('config.json'):
        raise Exception('config file not found.')

    with open('config.json', 'r') as json_data_file:
        config = loads(json_data_file.read())

        return config


def _get_plugins_in_location(location):
    py_files = glob('**/*.py')
