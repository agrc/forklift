#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import logging
import settings
from json import dumps
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
