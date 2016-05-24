#!/usr/bin/env python
# * coding: utf8 *
'''
models.py

A module that contains the model classes for forklift
'''


import logging
import settings
from os.path import join


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
        self._crates = []

    def process(self):
        '''This method will be called by forklift if any of the crates data is modified
        '''
        return NotImplemented

    def ship(self):
        '''this method fires whether the crates have any updates or not
        '''
        return NotImplemented

    def get_crates(self):
        '''returns an array of crates affected by the pallet. This is a self documenting way to know what layers an
        application is using.

        set `self.crates` in your child pallet.
        '''

        return self._crates

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

            self._crates.append(Crate(**params))

    def add_crate(self, crate_info):
        self.add_crates([crate_info])

    def validate_crate(self, crate):
        '''override to provide your own validation to determine whether the data within
        a create is ready to be updated

        this method should return a boolean indicating if the crate is ready for an update

        if this method is not overriden then the default validate within core is used
        '''
        return NotImplemented

    def is_ready_to_ship(self):
        '''checks to see if there are any schema changes or errors within the crates
        associated with this pallet

        returns: Boolean
        Returns True if there are no crates defined
        '''
        #: TODO
        return True

    def requires_processing(self):
        '''checks to see if any of the crates were updated

        returns: Boolean
        Returns False if there are no crates defined
        '''
        #: TODO
        return True

    def get_report(self):
        '''returns a message about the result of each crate in the plugin'''
        pass


class Crate(object):
    '''A module that defines a source and destination dataset that is a dependency of a pallet
    '''

    #: possible results returned from core.update_crate
    CREATED = 'Created table successfully.'
    UPDATED = 'Data updated successfully.'
    INVALID_DATA = 'Data is invalid. {}'
    NO_CHANGES = 'No changes found.'
    UNHANDLED_EXCEPTION = 'Unhandled exception during update.'
    UNINITIALIZED = 'This crate was never processed.'

    def __init__(self, source_name, source_workspace, destination_workspace, destination_name=None):
        #: the name of the source data table
        self.source_name = source_name
        #: the name of the source database
        self.source_workspace = source_workspace
        #: the name of the destination database
        self.destination_workspace = destination_workspace
        #: the name of the output data table
        self.destination_name = destination_name or source_name
        #: the result of the core.update method being called on this crate
        self.result = self.UNINITIALIZED

        self.source = join(source_workspace, source_name)
        self.destination = join(destination_workspace, self.destination_name)

    def set_result(self, value):
        self.result = value

        return value
