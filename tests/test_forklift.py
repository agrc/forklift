#!/usr/bin/env python
# * coding: utf8 *
'''
test_forklift.py

A module for testing forklift.py
'''

import unittest
from forklift import forklift
from forklift.models import Pallet, Crate
from mock import Mock


class TestForklift(unittest.TestCase):
    def setUp(self):
        self.update_crate = Crate('', '', 'a', '')
        self.update_crate.result = Crate.UPDATED

    def test_process_crate_for_single_update(self):
        update_crate = Crate('', '', 'a', '')
        pallet = Pallet('pallet1')
        pallet.add_crate(update_crate)
        update_def = Mock(return_value=Crate.UPDATED)
        forklift.process_crates_for([pallet], update_def)

        update_def.assert_called_once()
        self.assertEquals(update_crate.result, Crate.UPDATED)
