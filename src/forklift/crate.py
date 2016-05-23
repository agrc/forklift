#!/usr/bin/env python
# * coding: utf8 *
'''
crate.py

A module that defines a source and destination dataset that is a dependency of a pallet
'''


class Crate(object):
    def __init__(self, source_name, source=None, destination=None, destination_name=None, defaults=None):
        #: apply defaults, if any
        if defaults is not None:
            if 'source' in defaults.keys():
                self.source = defaults['source']
            if 'destination' in defaults.keys():
                self.destination = defaults['destination']

        #: the name of the source data table
        self.source_name = source_name

        #: the name of the source database
        if source:
            self.source = source
        if self.source is None:
            raise TypeError('source or defaults[\'source\'] is required!')

        #: the name of the destination database
        if destination:
            self.destination = destination
        if self.destination is None:
            raise TypeError('destination or defaults[\'destination\'] is required!')

        #: the name of the output data table
        self.destination_name = destination_name or source_name
