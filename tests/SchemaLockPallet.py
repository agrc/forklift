#!/usr/bin/env python
# * coding: utf8 *
'''
SchemaLockPallet.py

A module that contains Pallets to test forklift with data that is being used by arcgis server service.
These can be thought of as acceptance/exploritory tests.
'''
from os import path

from forklift.models import Pallet

data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')


class SchemaLockedPallet(Pallet):

    def __init__(self):
        super(SchemaLockedPallet, self).__init__()

        self.arcgis_services = [('forklift/SchemaLock', 'MapServer')]

        source_workspace = path.join(data_folder, 'NewSchemaData.gdb')
        destination_workspace = path.join(data_folder, 'SchemaLock.gdb')
        copy_to = destination_workspace

        self.add_crate('Empty', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})

        self.copy_data = [copy_to]


class NoSchemaLockPallet(Pallet):

    def __init__(self):
        super(NoSchemaLockPallet, self).__init__()

        self.arcgis_services = [('forklift/NoSchemaLock', 'MapServer')]

        source_workspace = path.join(data_folder, 'NewSchemaData.gdb')
        destination_workspace = path.join(data_folder, 'NoSchemaLock.gdb')
        copy_to = destination_workspace

        self.add_crate('Empty', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})

        self.copy_data = [copy_to]
