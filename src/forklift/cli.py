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

    return _set_config_folders(default_pallet_locations)


def add_config_folder(folder):
    folders = get_config_folders()

    if folder in folders:
        return '{} is already in the config folders list!'.format(folder)

    try:
        _validate_config_folder(folder, raises=True)
    except Exception as e:
        return e.message

    folders.append(folder)

    _set_config_folders(folders)

    return 'added {}'.format(folder)


def remove_pallet_folder(folder):
    folders = get_config_folders()

    try:
        folders.remove(folder)
    except ValueError:
        return '{} is not in the config folders list!'.format(folder)

    return _set_config_folders(folders)


def list_pallets(folders=None):
    if folders is None:
        folders = get_config_folders()

    return _get_pallets_in_folders(folders)


def list_config_folders():
    folders = get_config_folders()

    for folder in folders:
        yield _validate_config_folder(folder)


def _set_config_folders(folders):
    if type(folders) != list:
        raise Exception('config file data must be a list.')

    with open('config.json', 'w') as json_data_file:
        data = dumps(folders)

        log.debug('writing %s to %s', data, abspath(json_data_file.name))
        json_data_file.write(data)

        return abspath(json_data_file.name)


def get_config_folders():
    if not exists('config.json'):
        raise Exception('config file not found.')

    with open('config.json', 'r') as json_data_file:
        config = loads(json_data_file.read())

        return config


def _validate_config_folder(folder, raises=False):
    if exists(folder):
        valid = 'valid'
    else:
        valid = 'invalid!'
        if raises:
            raise Exception('{}: {}'.format(folder, valid))

    print('{}: {}'.format(folder, valid))


def _get_pallets_in_folders(folders):
    pallets = []

    for folder in folders:
        sys.path.append(folder)

        for py_file in glob(join(folder, '*.py')):
            pallets.extend(_get_pallets_in_file(py_file))

    return pallets


def _get_pallets_in_file(file_folder):
    pallets = []
    name = splitext(basename(file_folder))[0]
    mod = __import__(name)

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                pallets.append((file_folder, member))
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
        PalletClass = getattr(__import__(splitext(basename(info[0]))[0]), info[1])
        pallet = PalletClass('{}::{}'.format(basename(info[0], info[1]))

        pallet.process()
