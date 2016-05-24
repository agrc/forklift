#!/usr/bin/env python
# * coding: utf8 *
'''
test_forklift.py

A module for testing forklift.py
'''

import unittest
from forklift import forklift
from forklift.models import Pallet, Crate


class TestForklift(unittest.TestCase):
    def test_process_crates(self):
        default_crate_options = {'source_name': 'Name',
                                 'source': 'Blah.sde',
                                 'destination': 'Blah.gdb'}
        pallet_one = Pallet('pallet one')
        another_crate_options = default_crate_options.copy()
        another_crate_options['destination_name'] = 'Different'
        pallet_one.crates = [Crate(**default_crate_options),
                             Crate(**another_crate_options)]
        pallet_two = Pallet('pallet two')
        another_crate_options['destination_name'] = 'DifferentAgain'
        pallet_two.crates = [Crate(**default_crate_options),
                             Crate(**another_crate_options)]

        forklift.process_crates([pallet_one, pallet_two])
