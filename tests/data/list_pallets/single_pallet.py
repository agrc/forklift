#!/usr/bin/env python
# * coding: utf8 *
'''
single_pallet.py

A module that contains pallets to be used in test_lift.py tests
'''

from forklift.models import Pallet


class SinglePallet(Pallet):

    def __init__(self, name):
        super(SinglePallet, self).__init__()
        self.dependencies = ['a', 'b']
