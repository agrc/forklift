#!/usr/bin/env python
# * coding: utf8 *
'''
models.py

A module that contains the model classes for forklift
'''


import logging
import settings
from pprint import PrettyPrinter
from os.path import join


pprinter = PrettyPrinter()


class Pallet(object):
    '''A module that contains the base class that should be inherited from when building new pallet classes.

    Pallets are plugins for the forklift main process. They define a list of crates and
    any post processing that needs to happen.
    '''

    def __init__(self):
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger(settings.LOGGER)
        #: the table names for all dependent data for an application
        self._crates = []
        #: the status of the pallet (successful: Bool, message: string)
        self.success = (True, None)

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
        crate_param_names = ['source_name', 'source_workspace', 'destination_workspace', 'destination_name']

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
        for crate in self._crates:
            if crate.result in [Crate.INVALID_DATA, Crate.UNHANDLED_EXCEPTION]:
                return False

        return True

    def requires_processing(self):
        '''checks to see if any of the crates were updated

        returns: Boolean
        Returns False if there are no crates defined
        '''

        has_updated = False
        for crate in self._crates:
            if crate.result in [Crate.INVALID_DATA, Crate.UNHANDLED_EXCEPTION]:
                return False
            if not has_updated:
                has_updated = crate.result == Crate.UPDATED

        return has_updated

    def get_report(self):
        '''returns a message about the result of each crate in the plugin'''
        return ['{}: {}'.format(c.destination, c.result) for c in self.get_crates()]

    def __repr__(self):
        return pprinter.pformat({
            'crates': self._crates,
            'is_ready_to_ship': self.is_ready_to_ship(),
            'requires_processing': self.requires_processing()
        })


class Crate(object):
    '''A module that defines a source and destination dataset that is a dependency of a pallet
    '''

    #: possible results returned from core.update_crate
    CREATED = 'Created table successfully.'
    UPDATED = 'Data updated successfully.'
    INVALID_DATA = 'Data is invalid.'
    NO_CHANGES = 'No changes found.'
    UNHANDLED_EXCEPTION = 'Unhandled exception during update.'
    UNINITIALIZED = 'This crate was never processed.'

    def __init__(self,
                 source_name,
                 source_workspace,
                 destination_workspace,
                 destination_name=None,
                 destination_coordinate_system=None,
                 geographic_transformation=None):
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
        #: optional definition of destination coordinate system to support reprojecting
        self.destination_coordinate_system = destination_coordinate_system
        #: optional geographic transformation to support reprojecting
        self.geographic_transformation = geographic_transformation

        self.source = join(source_workspace, source_name)
        self.destination = join(destination_workspace, self.destination_name)

    def set_result(self, value):
        '''Sets the result of processing a crate.

        Returns the value of what was set'''
        acceptable_results = [self.CREATED, self.UPDATED, self.INVALID_DATA, self.NO_CHANGES, self.UNHANDLED_EXCEPTION, self.UNINITIALIZED]

        if value[0] in acceptable_results:
            self.result = value
        else:
            self.result = value = ('unknown result', value)

        return value

    def __repr__(self):
        return pprinter.pformat({
            'source': self.source,
            'destination': self.destination,
            'result': self.result,
            'source_name': self.source_name,
            'source_workspace': self.source_workspace,
            'destination_name': self.destination_name,
            'destination_workspace': self.destination_workspace,
            'destination_coordinate_system': self.destination_coordinate_system,
            'geographic_transformation': self.geographic_transformation
        })
