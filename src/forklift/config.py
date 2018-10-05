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
    '''stubs out a config file with default values
    '''
    try:
        makedirs(dirname(config_location))
    except Exception:
        pass

    with open(config_location, 'w') as json_config_file:
        data = {
            'configuration': 'Production',
            'dropoffLocation': 'c:\\forklift\\data\\receiving',
            'email': {
                'smtpServer': 'send.state.ut.us',
                'smtpPort': 25,
                'fromAddress': 'noreply@utah.gov'
            },
            'hashLocation': 'c:\\forklift\\data\\hashed',
            'notify': ['stdavis@utah.gov', 'sgourley@utah.gov'],
            'poolProcesses': default_num_processes,
            'repositories': [],
            'sendEmails': False,
            'servers': {
                'options': {
                    'protocol': 'http',
                    'port': 6080,
                    'username': '',
                    'password': ''
                },
                'primary': {
                    'machineName': 'machine.name.here'
                }
            },
            'serverStartWaitSeconds': 300,
            'shipTo': ['c:\\forklift\\data\\production'],
            'warehouse': default_warehouse_location
        }

        json_config_file.write(dumps(data, sort_keys=True, indent=2, separators=(',', ': ')))

        return abspath(json_config_file.name)


def _get_config():
    '''returns a dictionary representing the current config file (creating one if it doesn't not already exist)
    '''
    #: write default config if the file does not exist
    if not exists(config_location):
        create_default_config()

    with open(config_location, 'r') as json_config_file:
        return loads(json_config_file.read())


def get_config_prop(key):
    '''key: string

    returns the config value for the specified key
    '''
    if key.lower() != 'servers':
        return _get_config()[key]

    servers = _get_config()[key]
    if 'options' not in servers.keys():
        return servers

    options = servers.pop('options')
    for key, item in servers.items():
        temp = options.copy()
        temp.update(item)
        servers[key] = temp

    return servers


def set_config_prop(key, value, override=False):
    '''
    key: string
    value: any
    override: boolean

    Sets the key for the config to the passed in value.

    returns a string describing the results
    '''
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
