#!/usr/bin/env python
# * coding: utf8 *
'''
PalletSamples.py

A module that contains a sample Pallets to test forklift. These can be thought of as acceptance tests.
We should be able to run them twice without errors. Once to create, and once to check for updates.
'''

from forklift.models import Pallet
from os import path


data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')
destination_workspace = path.join(data_folder, 'SampleDestination')


class StringCratePallet(Pallet):

    def __init__(self):
        super(StringCratePallet, self).__init__()

        source_workspace = path.join(data_folder, 'agrc@sgid10.sde')

        self.add_crate('Counties', {'source_workspace': source_workspace,
                                    'destination_workspace': destination_workspace})

        self.copy_data = [destination_workspace]


class ExplicitCratePallet(Pallet):

    def __init__(self):
        super(ExplicitCratePallet, self).__init__()

        source_workspace = path.join(data_folder, 'agrc@sgid10.sde')

        crate_info = ('SGID10.GEOSCIENCE.AvalanchePaths', source_workspace, destination_workspace, 'AvyPaths')
        self.add_crate(crate_info)

        self.copy_data = [destination_workspace]


class OneValueTupleCratePallet(Pallet):

    def __init__(self):
        super(OneValueTupleCratePallet, self).__init__()

        source_workspace = path.join(data_folder, 'agrc@sgid10.sde')

        crate_info = ('SGID10.GEOSCIENCE.AvalanchePaths')
        self.add_crate(crate_info, {'source_workspace': source_workspace,
                                    'destination_workspace': destination_workspace})


class ShapefileCratePallet(Pallet):

    def __init__(self):
        super(ShapefileCratePallet, self).__init__()

        source_workspace = path.join(data_folder, 'myshape.shp')

        self.add_crate('myshape', {'source_workspace': source_workspace,
                                   'destination_workspace': destination_workspace})

    def ship(self):
        self.send_email('stdavis@utah.gov', 'test email', 'hello')


class SdeCratePallet(Pallet):

    def __init__(self):
        super(SdeCratePallet, self).__init__()

        destination_workspace = path.join(data_folder, 'UPDATE_TESTS.sde')
        source_workspace = path.join(data_folder, 'agrc@sgid10.sde')

        self.add_crate('SGID10.Boundaries.Counties', {'source_workspace': source_workspace,
                                                      'destination_workspace': destination_workspace})
