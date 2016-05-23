#!/usr/bin/env python
# * coding: utf8 *
'''
pallet.py

A module that contains the base class that should be inherited from when building new pallet classes.

Pallets are plugins for the forklift main process. They define a list of crates and
any post processing that needs to happen.
'''

import logging
import settings
from os.path import join


class Pallet(object):

    def __init__(self):
        #: the table names for all dependent data for an application
        self.dependencies = []
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger(settings.LOGGER)
        #: the parent path to where the source data is
        self.source_directory = 'C:\\MapData\\'
        #: the path to where the data in dependencies resides
        self.source_location = 'SGID10.sde'
        #: the parent path to where the output will be created
        self.output_directory = 'C:\\MapData\\'
        #: the file geodatabase where data will be inserted
        self.output_gdb_name = 'SGID10.gdb'

    def execute(self):
        '''This method will be called by forklift if the `expires_in_hours` value has expired.
        '''
        pass

    def get_dependent_layers(self):
        '''returns an array of layers affected by the pallet. This is a self documenting way to know what layers an
        application is using.

        set `self.dependencies` in your child pallet.
        '''

        return self.dependencies

    def get_source_location(self):
        '''returns `self.source_directory` + `self.location_source` which is the parent path to the data in
        `self.dependencies`.

        Default: `C:\\MapData\\SGID10.sde`
        '''

        return join(self.source_directory, self.source_location)

    def get_destination_location(self):
        '''returns `self.output_directory` + `self.output_gdb_name` which is where the data from `self.dependencies` will be
        placed.

        Default: `C:\\MapData\\SGID10.gdb`
        '''

        return join(self.output_directory, self.output_gdb_name)
