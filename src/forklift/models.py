#!/usr/bin/env python
# * coding: utf8 *
'''
models.py

A module that contains the model classes for forklift
'''

import logging
from inspect import getsourcefile
from os.path import dirname, join
from time import clock

from xxhash import xxh64

import arcpy

from . import config, seat
from .messaging import send_email

names_cache = {}


class Pallet(object):
    '''A module that contains the base class that should be inherited from when building new pallet classes.

    Pallets are plugins for the forklift main process. They define a list of crates and
    any post processing that needs to happen.

    In order for a pallet to be recognized by forklift, the file within which it is defined needs to have
    `pallet` (case-insensitive) somewhere in the filename.

    Multiple pallets with the same filename will cause issues so it's strongly recommended to keep them unique.
    Appending the project name to the file name is the convention.
    '''

    def __init__(self, arg=None):
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger('forklift')
        #: the table names for all dependent data for an application
        self._crates = []
        #: the status of the pallet (successful: Bool, message: string)
        self.success = (True, None)
        #: a list databases or folders that you want forklift to copy to `dropoffLocations`
        #: after a successful process
        self.copy_data = []
        #: default output coordinate system and transformation
        self.destination_coordinate_system = arcpy.SpatialReference(3857)
        self.geographic_transformation = 'NAD_1983_To_WGS_1984_5'
        #: a unique name for this pallet
        self.name = '{}:{}'.format(getsourcefile(self.__class__), self.__class__.__name__)
        #: the location of the garage containing logs and sde connection files etc
        self.garage = dirname(config.config_location)
        #: the default location to stage geodatabases. For use when creating crates
        self.staging_rack = config.get_config_prop('hashLocation')
        self.send_email = send_email
        self.total_processing_time = 0
        self.processing_times = {}
        self.timers = {}

    def build(self, configuration='Production'):
        '''configuration: string `Production`, `Staging`, or `Dev`

        Invoked before process and ship. Any logic that could cause a pallet to error
        should be placed in here instead of the `__init__` method.
        '''
        return

    def prepare_packaging(self):
        '''Invoked before process and ship only if this pallet is being lifted explicitly.
        '''
        return

    def process(self):
        '''Invoked if any crates have data updates.
        '''
        return NotImplemented

    def post_copy_process(self):
        '''Invoked after lift.copy_data has been called only if any crates have data updates.
        '''
        return NotImplemented

    def ship(self):
        '''Invoked whether the crates have updates or not.
        '''
        return NotImplemented

    def get_crates(self):
        '''Returns an array of crates affected by the pallet. This is a self documenting way to know what data an
        application is using.
        '''
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
        The third value sets `destination_workspace`. The fourth value sets `destination_name`. `defaults` is unused.
        '''
        crate_param_names = ['source_name', 'source_workspace', 'destination_workspace', 'destination_name']

        for info in crate_infos:
            params = defaults.copy()
            params.update({'destination_coordinate_system': self.destination_coordinate_system, 'geographic_transformation': self.geographic_transformation})

            #: info can be a table name here instead of a tuple
            if isinstance(info, str):
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
        '''crate: Crate

        Override to provide your own validation to determine whether the data within
        a create is ready to be updated.

        This method should return `True` if the crate is ready for an update. Otherwise it
        should raise `exceptions.ValidationException`.
        If this method is not overriden the default validate method within core is used.
        '''
        return NotImplemented

    def is_ready_to_ship(self):
        '''Returns True if there are not any schema changes or errors within the crates
        associated with the pallet. Returns True if there are no crates defined.

        Override this method to make pallets ship on a different schedule

        returns: Boolean
        '''
        return self.are_crates_valid() and self.success[0]

    def requires_processing(self):
        '''Returns True if any crates were updated. Returns False if there are no crates defined.

        returns: Boolean
        '''
        if not self.are_crates_valid():
            return False

        for crate in self._crates:
            if crate.was_updated():
                return True

        return False

    def are_crates_valid(self):
        '''Returns True if there are not any schema changes or errors within the crates
        associated with the pallet. Returns True if there are no crates defined.

        returns: Boolean
        '''
        for crate in self._crates:
            if crate.result[0] in [Crate.INVALID_DATA, Crate.UNHANDLED_EXCEPTION]:
                return False

        return True

    def start_timer(self, name):
        '''name: string

        sets a new time in timers
        '''
        self.timers[name] = clock()

    def stop_timer(self, name):
        '''name: string

        Records a processing time and adds it to the total processing time for the pallet.
        '''
        processing_time = self.processing_times.setdefault(name, 0)
        processing_time += clock() - self.timers[name]

        self.processing_times[name] = processing_time
        self.total_processing_time += processing_time

    def get_report(self):
        '''Returns an object with data about the results of the pallet for use in the report.
        '''
        return {
            'name': self.name,
            'success': self.success[0] and self.are_crates_valid(),
            'is_ready_to_ship': self.is_ready_to_ship(),
            'requires_processing': self.requires_processing(),
            'message': self.success[1] or '',
            'crates': [crate.get_report() for crate in self._crates if crate.get_report() is not None],
            'total_processing_time': seat.format_time(self.total_processing_time)
        }

    def add_packing_slip(self, slip):
        '''slip: object

        Adds the slip to the pallet
        '''
        self.slip = slip

    def __repr__(self):
        '''Override for better logging. Use with %r
        '''
        return self.name


class Crate(object):
    '''A module that defines a source and destination dataset that is a dependency of a pallet.
    '''

    #: possible results returned from core.update_crate
    CREATED = 'Created table successfully.'
    UPDATED = 'Data updated successfully.'
    INVALID_DATA = 'Data is invalid.'
    WARNING = 'Warning generated during update. Data not modified.'
    UPDATED_OR_CREATED_WITH_WARNINGS = 'Warning generated during update and data updated successfully.'
    NO_CHANGES = 'No changes found.'
    UNHANDLED_EXCEPTION = 'Unhandled exception during update.'
    UNINITIALIZED = 'This crate was never processed.'
    ERROR = 'There was an error.'  #: This can be used to manually set an error on a crate from within a pallet.

    def __init__(
        self,
        source_name,
        source_workspace,
        destination_workspace,
        destination_name=None,
        destination_coordinate_system=None,
        geographic_transformation=None,
        describer=arcpy.Describe
    ):
        #: the logging module to keep track of the crate
        self.log = logging.getLogger('forklift')
        #: the name of the source data table
        self.source_name = source_name
        #: the name of the source database
        self.source_workspace = source_workspace.lower()
        #: the name of the destination database
        self.destination_workspace = destination_workspace.lower()
        #: the result of the core.update method being called on this crate
        self.result = (self.UNINITIALIZED, None)
        #: the name of the output data table
        self.destination_name = destination_name or source_name

        #: crate_valid_table_name using env.workspace for the rules
        temp = arcpy.env.workspace
        arcpy.env.workspace = destination_workspace
        valid_destination_name = arcpy.ValidateTableName(self.destination_name)
        arcpy.env.workspace = temp

        if valid_destination_name != self.destination_name:
            self.result = (Crate.INVALID_DATA, 'Validation error with destination_name: {} != {}'.format(self.destination_name, valid_destination_name))

        #: optional definition of destination coordinate system to support reprojecting
        if destination_coordinate_system is not None and isinstance(destination_coordinate_system, int):
            destination_coordinate_system = arcpy.SpatialReference(destination_coordinate_system)

        self.destination_coordinate_system = destination_coordinate_system
        #: optional geographic transformation to support reprojecting
        self.geographic_transformation = geographic_transformation
        #: the full path to the destination data
        self.destination = join(self.destination_workspace, self.destination_name)
        #: the hash table name of a crate
        self.name = '{1}_{0}'.format(xxh64(self.destination).hexdigest(), self.destination_name).replace('.', '_')

        #: the full path to the source data
        self.source = join(source_workspace, source_name)

        if not arcpy.Exists(self.source):
            status, message = self._try_to_find_data_source_by_name()
            if not status:
                self.result = (Crate.INVALID_DATA, message)
                return

        try:
            self.source_describe = describer(self.source)
        except IOError as e:
            self.result = (Crate.INVALID_DATA, e)
            return

    def set_source_name(self, value):
        '''value: string

        Sets the source_name and updates the source property
        '''
        if value is None:
            return

        self.source_name = value
        self.source = join(self.source_workspace, value)

    def set_result(self, value):
        '''value: (String, String)

        Sets the result of processing a crate.

        Returns the value of what was set
        '''
        acceptable_results = [
            self.CREATED, self.UPDATED, self.INVALID_DATA, self.NO_CHANGES, self.UNHANDLED_EXCEPTION, self.UNINITIALIZED, self.WARNING,
            self.UPDATED_OR_CREATED_WITH_WARNINGS
        ]

        if value[0] in acceptable_results:
            self.result = value
        else:
            self.result = ('unknown result', value)

        return self.result

    def get_report(self):
        '''Returns the relavant info related to this crate that is shown on the report as a dictionary
        '''
        status = self.result[0]
        if status == self.NO_CHANGES:
            return None

        if status in [self.WARNING, self.UNINITIALIZED, self.UPDATED_OR_CREATED_WITH_WARNINGS]:
            message_level = 'warning'
        elif status in [self.UNHANDLED_EXCEPTION, self.INVALID_DATA, self.ERROR]:
            message_level = 'error'
        else:
            message_level = ''

        return {'name': self.destination_name,
                'result': self.result[0],
                'crate_message': self.result[1] or '',
                'message_level': message_level,
                'source': self.source,
                'destination': self.destination,
                'was_updated': self.was_updated()}

    def is_table(self):
        '''returns True if the crate defines a table
        '''
        return self.source_describe.datasetType.lower() == 'table'

    def needs_reproject(self):
        '''returns True if the crate needs to project between source and destination
        '''
        if self.is_table():
            return False

        if self.destination_coordinate_system is None:
            needs_reproject = False
        else:
            needs_reproject = self.destination_coordinate_system.name != self.source_describe.spatialReference.name

        return needs_reproject

    def was_updated(self):
        '''returns True if the crate was created or updated
        '''
        return self.result[0] in [Crate.CREATED, Crate.UPDATED, Crate.UPDATED_OR_CREATED_WITH_WARNINGS]

    def _try_to_find_data_source_by_name(self):
        '''try to find the source name in the source workspace.
        if it is found, update the crate name so subsequent uses do not fail.

        returns a tuple (bool, message) describing the outcome
        '''
        if '.sde' not in self.source.lower():
            return (None, 'Can\'t find data outside of sde')

        def filter_filenames(workspace, name):
            if workspace in names_cache:
                self.log.debug('cache hit for workspace: %s', workspace)
                names = names_cache[workspace]
            else:
                self.log.debug('cache miss for workspace: %s', workspace)
                arcpy.env.workspace = workspace

                def default_to_empty(list):
                    if list is None:
                        return []
                    return list

                names = default_to_empty(arcpy.ListFeatureClasses()) + default_to_empty(arcpy.ListTables())
                arcpy.env.workspace = None

                names_cache[workspace] = names

            #: could get a value like db.owner.***name and db.owner.name so filter on name
            return [fc for fc in names if fc.split('.')[2] == self.source_name]

        names = filter_filenames(self.source_workspace, self.source_name)

        if names is None or len(names) < 1:
            return (False, 'No source data found for {}'.format(self.source))

        if len(names) == 1:
            #: replace name with db.owner.name
            new_name = names[0]
            self.set_source_name(new_name)
            self.log.warning('Source name changed to %s', new_name)

            return (True, new_name)

        if len(names) > 1:
            return (False, 'Duplcate names: {}'.format(','.join(names)))

    def __repr__(self):
        '''Override for better logging. Use with %r
        '''

        return "source: [{}] source_workspace: [{}] destination: [{}]".format(self.source, self. source_workspace, self.destination)


class Changes(object):
    '''A module that contains the adds and deletes for when checking for changes.
    '''

    def __init__(self, fields):
        self.adds = {}
        self._deletes = {}
        self.unchanged = {}
        self.fields = fields
        self.table = ''
        self.total_rows = 0
        self.has_dups = False

    def has_adds(self):
        '''returns true if the source table has new rows
        '''
        return len(self.adds) > 0

    def has_deletes(self):
        '''returns true if the destination has rows that are not in the source
        '''
        return len(self._deletes) > 0

    def has_changes(self):
        '''returns true if has_adds or has_deletes return true
        '''
        return self.has_adds() or self.has_deletes()

    def determine_deletes(self, attribute_hashes):
        '''attribute_hashes: Dictionary<string, hash> of id's and hashes that were not accessed

        returns the deletes
        '''
        self._deletes = attribute_hashes

        return self._deletes
