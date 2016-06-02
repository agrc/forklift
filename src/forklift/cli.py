#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import core
import lift
import logging
import seat
import settings
import sys
from glob import glob
from json import dumps, loads
from models import Pallet
from os.path import abspath, exists, join, splitext, basename, dirname
from time import clock

log = logging.getLogger(settings.LOGGER)


def init():
    if exists('config.json'):
        return abspath('config.json')

    default_pallet_locations = ['c:\\scheduled']

    return _set_config_folders(default_pallet_locations)


def add_config_folder(folder):
    folders = _get_config_folders()

    if folder in folders:
        return '{} is already in the config folders list!'.format(folder)

    try:
        _validate_config_folder(folder, raises=True)
    except Exception as e:
        return e.message

    folders.append(folder)

    _set_config_folders(folders)

    return '{} added'.format(folder)


def remove_config_folder(folder):
    folders = _get_config_folders()

    try:
        folders.remove(folder)
    except ValueError:
        return '{} is not in the config folders list!'.format(folder)

    _set_config_folders(folders)

    return '{} removed'.format(folder)


def list_pallets(folders=None):
    if folders is None:
        folders = _get_config_folders()

    return _get_pallets_in_folders(folders)


def list_config_folders():
    folders = _get_config_folders()

    validate_results = []
    for folder in folders:
        validate_results.append(_validate_config_folder(folder))

    return validate_results


def start_lift(file_path=None):
    log.info('starting forklift')
    start_seconds = clock()

    if file_path is not None:
        pallet_infos = _get_pallets_in_file(file_path)
    else:
        pallet_infos = list_pallets()

    pallets = []
    for info in pallet_infos:
        module_name = splitext(basename(info[0]))[0]
        class_name = info[1]
        PalletClass = getattr(__import__(module_name), class_name)
        pallets.append(PalletClass())

    lift.process_crates_for(pallets, core.update)

    log.info('elapsed time: %s', seat.format_time(clock() - start_seconds))

    for msg in lift.process_pallets(pallets):
        log.info(msg)
        print(msg)


def _set_config_folders(folders):
    if type(folders) != list:
        raise Exception('config file data must be a list.')

    #: write default config if the file does not exist
    if not exists('config.json'):
        return _create_default_config(folders)

    with open('config.json', 'r') as json_config_file:
        config = loads(json_config_file.read())

        if 'paths' not in config:
            return _create_default_config(folders)

    with open('config.json', 'w') as json_config_file:
        config['paths'] = folders
        json_config_file.write(dumps(config))

        return abspath(json_config_file.name)


def _create_default_config(folders):
    with open('config.json', 'w') as json_config_file:
        data = {
            'paths': folders,
            'logLevel': 'INFO',
            'logger': 'file',
            'notify': ['stdavis@utah.gov', 'sgourley@utah.gov']
        }

        json_config_file.write(dumps(data))

        return abspath(json_config_file.name)


def _get_config_folders():
    if not exists('config.json'):
        raise Exception('config file not found.')

    with open('config.json', 'r') as json_config_file:
        config = loads(json_config_file.read())

        return config['paths']


def _validate_config_folder(folder, raises=False):
    if exists(folder):
        message = '[Valid]'
    else:
        message = '[Folder not found]'
        if raises:
            raise Exception('{}: {}'.format(folder, message))

    return ('{}: {}'.format(folder, message))


def _get_pallets_in_folders(folders):
    pallets = []

    for folder in folders:
        for py_file in glob(join(folder, '*.py')):
            pallets.extend(_get_pallets_in_file(py_file))

    return pallets


def _get_pallets_in_file(file_path):
    pallets = []
    name = splitext(basename(file_path))[0]
    folder = dirname(file_path)

    if folder not in sys.path:
        sys.path.append(folder)

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
