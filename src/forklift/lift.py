#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import logging
import settings
import sys
from plugin import ScheduledUpdateBase
from glob import glob
from json import dumps, loads
from os.path import abspath, exists, join, splitext, basename

log = logging.getLogger(settings.LOGGER)


def init():
    if exists('config.json'):
        return 'config file already created.'

    default_plugin_locations = ['c:\\scheduled']

    log.debug('creating config.json file.')
    return _set_config_paths(default_plugin_locations)


def add_plugin_folder(path):
    paths = get_config_paths()
    paths.append(path)
    return _set_config_paths(paths)


def list_plugins(paths=None):
    if paths is None:
        paths = get_config_paths()

    return _get_plugins_in_location(paths)


def _set_config_paths(paths):
    if type(paths) != list:
        raise Exception('config file data must be a list.')

    with open('config.json', 'w') as json_data_file:
        data = dumps(paths)

        log.debug('writing %s to %s', data, abspath(json_data_file.name))
        json_data_file.write(data)

        return abspath(json_data_file.name)


def get_config_paths():
    if not exists('config.json'):
        raise Exception('config file not found.')

    with open('config.json', 'r') as json_data_file:
        config = loads(json_data_file.read())

        return config


def _get_plugins_in_location(paths):
    plugins = []
    for path in paths:
        sys.path.append(path)
        for py_file in glob(join(path, '*.py')):
            name = splitext(basename(py_file))[0]
            mod = __import__(name)
            for member in dir(mod):
                try:
                    potential_class = getattr(mod, member)
                    if issubclass(potential_class, ScheduledUpdateBase) and potential_class != ScheduledUpdateBase:
                        plugins.append((py_file, member))
                except:
                    # member was likely not a class
                    pass
    return plugins
