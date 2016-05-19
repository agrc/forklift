#!/usr/bin/env python
# * coding: utf8 *
'''
plugin.py

A module that contains the plugin class that should be inherited from when building plugins
'''

import logging
import settings
from os.path import join


class ScheduledUpdateBase(object):

    def __init__(self):
        #: the logging module to keep track of the plugin
        self.log = logging.getLogger(settings.LOGGER)
        #: the duration in hours that marks a plugin as dirty
        self.expires_in_hours = 24
        #: the path to where the data in dependencies resides
        self.source_location = 'C:\\MapData\\SGID10.sde'
        #: the parent path to where the output will be created
        self.output_directory = 'C:\\MapData\\'
        #: the file geodatabase where data will be inserted
        self.gdb_name = 'SGID10.gdb'
        #: the table names for all dependent data for an application
        self.dependencies = []

    def nightly(self):
        '''This method will be called by forklift if the `expires_in_hours` value has expired.
        This is the only method that needs to be implemented and will otherwise throw a `NotImplementedError`.
        '''

        raise NotImplementedError('Implement nightly in your child plugin.')

    def get_dependent_layers(self):
        '''returns an array of layers affected by the plugin. This is a self documenting way to know what layers an
        application is using.

        set `self.dependencies` in your child plugin.
        '''

        return self.dependencies

    def get_source_location(self):
        '''returns `self.ouput_directory + self.location source` which is the parent path to the data in
        `self.dependencies`.

        Default: `C:\\MapData\\SGID10.sde`
        '''

        return self.source_location

    def get_destination_location(self):
        '''returns `self.output_directory` + `self.gdb_name` which is where the data from `self.dependencies` will be
        placed.

        Default: `C:\\MapData\\SGID10.gdb`
        '''

        return join(self.output_directory, self.gdb_name)
