#!/usr/bin/env python
# * coding: utf8 *
'''
PalletSamples.py

A module that contains a sample Pallets to test forklift. These can be thought of as acceptance tests.
We should be able to run them twice without errors. Once to create, and once to check for updates.
'''

from os import path

from forklift.models import Pallet

data_folder = path.join(path.dirname(path.realpath(__file__)), 'data')
destination_workspace = path.join(data_folder, 'SampleDestination.gdb')


# class StringCratePallet(Pallet):
#
#     def __init__(self):
#         #: this is required to initialize the Pallet base class properties
#         super(StringCratePallet, self).__init__()
#
#         self.copy_data = [destination_workspace]
#
#     def build(self, configuration):
#         source_workspace = path.join(data_folder, 'agrc@sgid10.sde')
#
#         self.add_crate('Counties', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})
#
#
# class ExplicitCratePallet(Pallet):
#
#     def __init__(self):
#         #: this is required to initialize the Pallet base class properties
#         super(ExplicitCratePallet, self).__init__()
#
#         self.copy_data = [destination_workspace]
#
#     def build(self, configuration):
#         source_workspace = path.join(data_folder, 'agrc@sgid10.sde')
#
#         crate_info = ('AvalanchePaths', source_workspace, destination_workspace, 'AvyPaths')
#         self.add_crate(crate_info)
#
#
# class OneValueTupleCratePallet(Pallet):
#
#     def __init__(self):
#         #: this is required to initialize the Pallet base class properties
#         super(OneValueTupleCratePallet, self).__init__()
#
#     def build(self, configuration):
#         source_workspace = path.join(data_folder, 'agrc@sgid10.sde')
#
#         crate_info = ('AvalanchePaths')
#         self.add_crate(crate_info, {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})
#
#
class ShapefileCratePallet(Pallet):

    def __init__(self):
        #: this is required to initialize the Pallet base class properties
        super(ShapefileCratePallet, self).__init__()

    def build(self, configuration):
        source_workspace = path.join(data_folder, 'myshape.shp')

        self.add_crate('myshape', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})

    def ship(self):
        self.send_email('stdavis@utah.gov', 'test email', 'hello')


#
# class SdeCratePallet(Pallet):
#
#     def __init__(self):
#         #: this is required to initialize the Pallet base class properties
#         super(SdeCratePallet, self).__init__()
#
#     def build(self, configuration):
#         destination_workspace = path.join(data_folder, 'UPDATE_TESTS.sde')
#         source_workspace = path.join(data_folder, 'agrc@sgid10.sde')
#
#         self.add_crate('Counties', {'source_workspace': source_workspace, 'destination_workspace': destination_workspace})
