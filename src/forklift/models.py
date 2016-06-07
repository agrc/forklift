#!/usr/bin/env python
# * coding: utf8 *
'''
models.py

A module that contains the model classes for forklift
'''


import logging
from arcpy import env, SpatialReference, ValidateTableName as create_valid_table_name
from inspect import getsourcefile
from pprint import PrettyPrinter
from os.path import join


pprinter = PrettyPrinter(indent=4, width=40)


class Pallet(object):
    '''A module that contains the base class that should be inherited from when building new pallet classes.

    Pallets are plugins for the forklift main process. They define a list of crates and
    any post processing that needs to happen.
    '''

    def __init__(self):
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger('forklift')
        #: the table names for all dependent data for an application
        self._crates = []
        #: the status of the pallet (successful: Bool, message: string)
        self.success = (True, None)
        self.name = '{}:{}'.format(getsourcefile(self.__class__), self.__class__.__name__)

    def process(self):
        '''Invoked if any crates have data updates.
        '''
        return NotImplemented

    def ship(self):
        '''Invoked whether the crates have updates or not.
        '''
        return NotImplemented

    def get_crates(self):
        '''Returns an array of crates affected by the pallet. This is a self documenting way to know what data an
        application is using.'''
        return self._crates

    def add_crates(self, crate_infos, defaults={}):
        '''crate_infos: [String | (source_name,
                                   source workspace,
                                   destintion workspace: optional if set with defaults,
                                   destination name: optional will default to source_name)]
        defaults: optional dictionary {source_workspace: '', destination_workspace: ''}

        Given an array of strings or tuples this method will create and add a `Crate` to the `_crates` list.

        If a `crate_infos` index is a string, a `Crate` is created with the value as `source_name` and `destination_name`.
        It is expected for `defaults` to contain `source_workspace` and `destination_workspace` vaules.

        If a `crate_infos` index is a tuple, the values are zipped with the `crate_param_names` list.

        If a tuple has 1 value, the value will be set to `source_name` and `destination_name`.
        The `defaults` need to contain `source_workspace` and `destination_workspace` vaules.
        If a tuple has 2 values, the first value is set to `source_name` and `destination_name`. The second value sets
        the `source_workspace` and `defaults` needs to contain `destination_workspace`. `source_workspace` is overriden.
        If a tuple has 3 values, the first value is set to `source_name` and `destination_name`. The second value sets
        the `source_workspace`. The third value sets `destination_workspace`. `defaults` is unused.
        If a tuple has 4 values, the first value is set to `source_name`. The second value sets `source_workspace`.
        The third value sets `destination_workspace`. The fourth value sets `destination_name`. `defaults` is unused.'''
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

    def add_crate(self, crate_info, defaults={}):
        '''Same as above but one at a time
        '''
        self.add_crates([crate_info], defaults)

    def validate_crate(self, crate):
        '''Override to provide your own validation to determine whether the data within
        a create is ready to be updated.

        This method should return a Boolean indicating if the crate is ready for an update.
        If this method is not overriden the default validate method within core is used.'''
        return NotImplemented

    def is_ready_to_ship(self):
        '''Returns True if there are not any schema changes or errors within the crates
        associated with the pallet. Returns True if there are no crates defined.

        returns: Boolean'''
        for crate in self._crates:
            if crate.result[0] in [Crate.INVALID_DATA, Crate.UNHANDLED_EXCEPTION]:
                return False

        return True

    def requires_processing(self):
        '''Returns True if any crates were updated. Returns False if there are no crates defined.

        returns: Boolean'''
        has_updated = False

        for crate in self._crates:
            if crate.result[0] in [Crate.INVALID_DATA, Crate.UNHANDLED_EXCEPTION]:
                return False
            if not has_updated:
                has_updated = crate.result[0] == Crate.UPDATED

        return has_updated

    def get_report(self):
        '''Returns a message about the result of each crate in the pallet.
        '''
        return {'name': self.name,
                'success': self.success[0] and self.is_ready_to_ship(),
                'message': self.success[1],
                'crates': [crate.get_report() for crate in self._crates]}

    def __repr__(self):
        '''Override for better logging. Use with %r
        '''
        return pprinter.pformat({
            'crate_count': len(self._crates),
            'is_ready_to_ship': self.is_ready_to_ship(),
            'requires_processing': self.requires_processing()
        })


class Crate(object):
    '''A module that defines a source and destination dataset that is a dependency of a pallet.
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

        temp = env.workspace
        env.workspace = destination_workspace

        #: the name of the output data table
        self.destination_name = create_valid_table_name(destination_name or source_name)

        env.workspace = temp
        #: the result of the core.update method being called on this crate
        self.result = self.UNINITIALIZED
        #: optional definition of destination coordinate system to support reprojecting
        if destination_coordinate_system is not None and isinstance(destination_coordinate_system, int):
            destination_coordinate_system = SpatialReference(destination_coordinate_system)

        self.destination_coordinate_system = destination_coordinate_system
        #: optional geographic transformation to support reprojecting
        self.geographic_transformation = geographic_transformation
        #: the full path to the source data
        self.source = join(source_workspace, source_name)
        #: the full path to the destination data
        self.destination = join(self.destination_workspace, self.destination_name)

    def set_source_name(self, value):
        '''Sets the source_name and updates the source property
        '''
        if value is None:
            return

        self.source_name = value
        self.source = join(self.source_workspace, value)

    def set_result(self, value):
        '''Sets the result of processing a crate.
        value: (String, String)

        Returns the value of what was set'''
        acceptable_results = [self.CREATED, self.UPDATED, self.INVALID_DATA, self.NO_CHANGES, self.UNHANDLED_EXCEPTION, self.UNINITIALIZED]

        if value[0] in acceptable_results:
            self.result = value
        else:
            self.result = value = ('unknown result', value)

        return value

    def get_report(self):
        '''Returns the relavant info related to this crate that is shown on the report as a dictionary'''
        return {'name': self.destination_name,
                'result': self.result[0],
                'crate_message': self.result[1]}

    def __repr__(self):
        '''Override for better logging. Use with %r
        '''
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
