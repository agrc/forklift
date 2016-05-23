#!/usr/bin/env python
# * coding: utf8 *
'''
crate.py

A module that defines a source and destination dataset that is a dependency of a pallet
'''


class Crate(object):

    def __init__(self, source_name, source, destination, destination_name=None):
        #: the name of the source data table
        self.source_name = source_name

        #: the name of the source database
        self.source = source

        #: the name of the destination database
        self.destination = destination

        #: the name of the output data table
        self.destination_name = destination_name or source_name
