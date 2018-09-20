#!/usr/bin/env python
# * coding: utf8 *

from os import path

from forklift.models import Pallet


class TypicalPallet(Pallet):

    def __init__(self):
        super(TypicalPallet, self).__init__()

        self.arcgis_services = [('Service', 'MapServer')]

        self.location_utm = path.join(self.staging_rack, 'location_utm.gdb')

        self.copy_data = [self.location_utm]
        self.destination_coordinate_system = 26912

    def build(self, configuration=None):
        data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')
        source_workspace = path.join(data_folder, 'SourceData.gdb')

        self.add_crates(['AddressPoints'], {'source_workspace': source_workspace, 'destination_workspace': self.location_utm})
