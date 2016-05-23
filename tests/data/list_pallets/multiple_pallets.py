#!/usr/bin/env python
# * coding: utf8 *
'''
multiple_pallets.py

A module that contains pallets to be used in test_lift.py tests
'''

from forklift.models import Pallet


class PalletOne(Pallet):

    def __init__(self):
        super(PalletOne, self).__init__()

        self.add_crates(['fc1',
                         'fc2',
                         ('fc3', 'source', 'destination'),
                         ('fc4', 'source', 'destination', 'fc4_new')],
                        {'source_workspace': 'C:\\MapData\\UDNR.sde',
                         'destination_workspace': 'C:\\MapData\\UDNR.gdb'})


class PalletTwo(Pallet):

    def __init__(self):
        super(PalletTwo, self).__init__()

    def ship(self):
        print('execute: overridden')
