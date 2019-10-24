#!/usr/bin/env python
# * coding: utf8 *

from os import path
from time import sleep

from forklift.models import Pallet


class TypicalPallet(Pallet):

    def __init__(self):
        super(TypicalPallet, self).__init__()

        self.arcgis_services = [('Service', 'MapServer')]

        self.boundaries_utm = path.join(self.staging_rack, 'boundaries_utm.gdb')

        self.copy_data = [self.boundaries_utm]
        self.destination_coordinate_system = 26912

    def build(self, configuration=None):
        data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')
        source_workspace = path.join(data_folder, 'SourceData.gdb')

        self.add_crates(['Counties'], {'source_workspace': source_workspace, 'destination_workspace': self.boundaries_utm})

    def ship(self):
        sleep(1)

    def post_copy_process(self):
        sleep(1)
