#!/usr/bin/env python
# * coding: utf8 *
'''
models.py

A module that contains the model classes for forklift
'''


import logging
import settings


class Pallet(object):
    '''A module that contains the base class that should be inherited from when building new pallet classes.

    Pallets are plugins for the forklift main process. They define a list of crates and
    any post processing that needs to happen.
    '''

    def __init__(self, name):
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger(settings.LOGGER)
        #: the name of the pallet
        self.name = name
        #: the table names for all dependent data for an application
        self.crates = []

    def process(self):
        '''This method will be called by forklift if any of the crates data is modified
        '''
        pass

    def get_crates(self):
        '''returns an array of crates affected by the pallet. This is a self documenting way to know what layers an
        application is using.

        set `self.crates` in your child pallet.
        '''

        return self.crates

    def add_crates(self, crate_infos, defaults={}):
        crate_param_names = ['source_name', 'source', 'destination', 'destination_name']

        for info in crate_infos:
            params = defaults.copy()

            #: info can be a table name here instead of a tuple
            if isinstance(info, basestring):
                params['source_name'] = info
            else:
                for i, val in enumerate(info):
                    params[crate_param_names[i]] = val

            self.crates.append(Crate(**params))

    def add_crate(self, crate_info):
        self.add_crates([crate_info])


class Crate(object):
    '''A module that defines a source and destination dataset that is a dependency of a pallet
    '''

    def __init__(self, source_name, source, destination, destination_name=None):
        #: the name of the source data table
        self.source_name = source_name
        #: the name of the source database
        self.source = source
        #: the name of the destination database
        self.destination = destination
        #: the name of the output data table
        self.destination_name = destination_name or source_name
        #: the unique name of the crate
        self.name = '{}::{}'.format(destination, destination_name)
