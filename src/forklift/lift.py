#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import logging
import settings
import sys
from pallet import Pallet
from glob import glob
from json import dumps, loads
from os.path import abspath, exists, join, splitext, basename

log = logging.getLogger(settings.LOGGER)


def init():
    if exists('config.json'):
        return 'config file already created.'

    default_pallet_locations = ['c:\\scheduled']

    log.debug('creating config.json file.')

    return _set_config_paths(default_pallet_locations)


def add_pallet_folder(path):
    paths = get_config_paths()

    if path in paths:
        return '{} is already in the config paths list!'.format(path)

    try:
        valid_config_path(path=path, raises=True):
    except Exception as e:
        return e.message

    paths.append(path)

    return _set_config_paths(paths)


def remove_pallet_folder(path):
    paths = get_config_paths()

    try:
        paths.remove(path)
    except ValueError:
        return '{} is not in the config paths list!'.format(path)

    return _set_config_paths(paths)


def list_pallets(paths=None):
    if paths is None:
        paths = get_config_paths()

    return _get_pallets_in_folders(paths)


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


def validate_config_paths(path=None, raises=False):
    if path is None:
        paths = get_config_paths()

    for path in paths:
        if exists(path):
            valid = 'valid'
        else:
            valid = 'invalid!'
            if raises:
                throw Exception('{}: {}'.format(path, valid))

        print('{}: {}'.format(path, valid))


def _get_pallets_in_folders(paths):
    pallets = []

    for path in paths:
        sys.path.append(path)

        for py_file in glob(join(path, '*.py')):
            pallets.extend(_get_pallets_in_file(py_file))

    return pallets


def _get_pallets_in_file(file_path):
    pallets = []
    name = splitext(basename(file_path))[0]
    mod = __import__(name)

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                pallets.append((file_path, member))
        except:
            #: member was likely not a class
            pass

    return pallets


def lift(file_path=None):
    if file_path is not None:
        pallet_infos = _get_pallets_in_file(file_path)
    else:
        pallet_infos = list_pallets()

    for info in pallet_infos:
        palletClass = getattr(__import__(splitext(basename(info[0]))[0]), info[1])
        pallet = palletClass()

        pallet.process()
