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

    if path in paths:
        raise Exception('{} is already in the config paths list!')

    paths.append(path)

    return _set_config_paths(paths)


def remove_plugin_folder(path):
    paths = get_config_paths()
    try:
        paths.remove(path)
    except ValueError:
        raise Exception('{} is not in the config paths list!')

    return _set_config_paths(paths)


def list_plugins(paths=None):
    if paths is None:
        paths = get_config_paths()

    return _get_plugins_in_folders(paths)


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


def validate_config_paths():
    paths = get_config_paths()

    for path in paths:
        if exists(path):
            valid = 'valid'
        else:
            valid = 'invalid!'
        print('{}: {}'.format(path, valid))


def _get_plugins_in_folders(paths):
    plugins = []
    for path in paths:
        sys.path.append(path)
        for py_file in glob(join(path, '*.py')):
            plugins.extend(_get_plugins_in_file(py_file))
    return plugins


def _get_plugins_in_file(file_path):
    plugins = []
    name = splitext(basename(file_path))[0]
    mod = __import__(name)
    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, ScheduledUpdateBase) and potential_class != ScheduledUpdateBase:
                plugins.append((file_path, member))
        except:
            #: member was likely not a class
            pass

    return plugins


def update(file_path=None):
    if file_path is not None:
        plugin_infos = _get_plugins_in_file(file_path)
    else:
        plugin_infos = list_plugins()

    for info in plugin_infos:
        PluginClass = getattr(__import__(splitext(basename(info[0]))[0]), info[1])
        plugin = PluginClass()

        #: not sure what needs to be done here want to do here
        print plugin.expires_in_hours
        plugin.execute()
