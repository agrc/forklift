#!/usr/bin/env python
# * coding: utf8 *
'''
SpeedTestPallet.py

A module that contains Pallets to test forklift speed. These can be thought of as acceptance tests.
We should be able to run them twice without errors. Once to create, and once to check for updates.
'''

from forklift.models import Pallet
from os import path

data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')
destination_workspace = path.join(data_folder, 'DestinationData.gdb')
source_workspace = path.join(data_folder, 'SourceData.gdb')


class LargeDataPallet(Pallet):

    def __init__(self):
        super(LargeDataPallet, self).__init__()

        self.add_crate('AddressPoints', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})


class SmallDataPallet(Pallet):

    def __init__(self):
        super(SmallDataPallet, self).__init__()

        self.destination_coordinate_system = 26912
        self.geographic_transformation = None
        self.add_crate('Counties', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})


class TablePallet(Pallet):

    def __init__(self):
        super(TablePallet, self).__init__()

        self.add_crate('SchoolInfo', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})


class ShapefilePallet(Pallet):

    def __init__(self):
        super(ShapefilePallet, self).__init__()

        self.add_crate(('Counties.shp', data_folder, destination_workspace, 'CountiesFromShapefile'))
