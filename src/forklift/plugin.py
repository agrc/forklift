#!/usr/bin/env python
# * coding: utf8 *
'''
plugin.py

A module that contains the plugin class that should be inherited from when building plugins
'''

import logging
import settings
from os.path import join
import venusian


def update(pattern, **extra):
    def deco(func):
        def callback(scanner, name, obj):
            scanner.register(pattern, obj, extra)
        venusian.attach(func, callback)
        return func
    return deco


class ScheduledUpdateBase(object):

    def __init__(self):
        #: the logging module to keep track of the plugin
        self.log = logging.getLogger(settings.LOGGER)
        #: the duration in hours that marks a plugin as dirty
        self.expires_in_hours = 24
        #: the parent path to where the source data is
        self.source_directory = 'C:\\MapData\\'
        #: the path to where the data in dependencies resides
        self.source_location = 'SGID10.sde'
        #: the parent path to where the output will be created
        self.output_directory = 'C:\\MapData\\'
        #: the file geodatabase where data will be inserted
        self.output_gdb_name = 'SGID10.gdb'
        #: the table names for all dependent data for an application
        self.dependencies = []

    def execute(self):
        '''This method will be called by forklift if the `expires_in_hours` value has expired.
        '''

        pass

    def get_dependent_layers(self):
        '''returns an array of layers affected by the plugin. This is a self documenting way to know what layers an
        application is using.

        set `self.dependencies` in your child plugin.
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
