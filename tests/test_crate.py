#!/usr/bin/env python
# * coding: utf8 *
'''
test_crate.py

A module for testing crate.py
'''

import unittest
from forklift.crate import Crate


class TestCrate(unittest.TestCase):
    def test_pass_all_values(self):
        crate = Crate('sourceName', 'blah', 'hello', 'blur')
        self.assertEquals(crate.source_name, 'sourceName')
        self.assertEquals(crate.source, 'blah')
        self.assertEquals(crate.destination, 'hello')
        self.assertEquals(crate.destination_name, 'blur')

    def test_destination_name_defaults_to_source(self):
        crate = Crate('sourceName', 'source', 'destination')
        self.assertEquals(crate.destination_name, crate.source_name)
