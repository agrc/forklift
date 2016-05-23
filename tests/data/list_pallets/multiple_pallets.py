#!/usr/bin/env python
# * coding: utf8 *
'''
multiple_pallets.py

A module that contains pallets to be used in test_lift.py tests
'''

from forklift.pallet import Pallet


class PalletOne(Pallet):

    def __init__(self):
        super(PalletOne, self).__init__()
        self.expires_in_hours = 1


class PalletTwo(Pallet):

    def __init__(self):
        super(PalletTwo, self).__init()
        self.expires_in_hours = 2
        self.dependencies = ['c', 'd']

    def execute(self):
        print('execute: overridden')
