#!/usr/bin/env python
# * coding: utf8 *
'''
multiple_pallets.py

A module that contains pallets to be used in test_lift.py tests
'''

from forklift.models import Pallet


class PalletOne(Pallet):

    def __init__(self, name):
        super(PalletOne, self).__init__()
        self.expires_in_hours = 1

        self.set_default_source_location()

        self.add_crates(['fc1',
                         'fc2',
                         ('fc3', 'source', 'destination'),
                         ('fc4', 'source', 'destination', 'fc4_new')],
                        {'source': 'C:\\MapData\\UDNR.sde',
                         'destination': 'C:\\MapData\\UDNR.gdb'})


class PalletTwo(Pallet):

    def __init__(self, name):
        super(PalletTwo, self).__init()
        self.expires_in_hours = 2
        self.dependencies = ['c', 'd']

    def execute(self):
        print('execute: overridden')
