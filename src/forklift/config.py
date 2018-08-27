#!/usr/bin/env python
# * coding: utf8 *
'''
config.py

A module that contains logic for reading and writing the config file
'''

import logging
from json import dumps, loads
from os import makedirs
from os.path import abspath, dirname, exists, join

log = logging.getLogger('forklift')
config_location = join(abspath(dirname(__file__)), '..', 'forklift-garage', 'config.json')
default_warehouse_location = 'c:\\scheduled\\warehouse'
default_staging_location = 'c:\\scheduled\\staging'
default_num_processes = 20


def create_default_config():
    try:
        makedirs(dirname(config_location))
    except Exception:
        pass

    with open(config_location, 'w') as json_config_file:
        data = {
            'configuration': 'Production',
            'warehouse': default_warehouse_location,
            'repositories': [],
            'copyDestinations': [],
            'stagingDestination': default_staging_location,
            'sendEmails': False,
            'notify': ['stdavis@utah.gov', 'sgourley@utah.gov']
        }

        json_config_file.write(dumps(data, sort_keys=True, indent=2, separators=(',', ': ')))

        return abspath(json_config_file.name)


def _get_config():
    #: write default config if the file does not exist
    if not exists(config_location):
        create_default_config()

    with open(config_location, 'r') as json_config_file:
        return loads(json_config_file.read())


def get_config_prop(key):
    return _get_config()[key]


def set_config_prop(key, value, override=False):
    config = _get_config()

    if key not in config:
        return '{} not found in config.'.format(key)

    if not override:
        try:
            if not isinstance(value, list):
                if value not in config[key]:
                    config[key].append(value)
                else:
                    return '{} already contains {}'.format(key, value)
            else:
                for item in value:
                    if item not in config[key]:
                        config[key].append(item)
        except AttributeError:
            #: prop is not an array set value instead of append
            config[key] = value
    else:
        config[key] = value

    with open(config_location, 'w') as json_config_file:
        json_config_file.write(dumps(config, sort_keys=True, indent=2, separators=(',', ': ')))

    return 'Added {} to {}'.format(value, key)
