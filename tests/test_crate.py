#!/usr/bin/env python
# * coding: utf8 *
'''
test_crate.py

A module for testing crate.py
'''

import unittest
from forklift.models import Crate


class TestCrate(unittest.TestCase):
    def test_pass_all_values(self):
        crate = Crate('sourceName', 'blah', 'hello', 'blur')
        self.assertEquals(crate.source_name, 'sourceName')
        self.assertEquals(crate.source_workspace, 'blah')
        self.assertEquals(crate.destination_workspace, 'hello')
        self.assertEquals(crate.destination_name, 'blur')

    def test_destination_name_defaults_to_source(self):
        crate = Crate('sourceName', 'source', 'destination')
        self.assertEquals(crate.destination_name, crate.source_name)

    def test_set_result_with_valid_result_returns_result(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        self.assertEquals(crate.set_result((Crate.UPDATED, 'Yay!'))[0], Crate.UPDATED)
        self.assertEquals(crate.result[0], Crate.UPDATED)

    def test_set_result_with_invalid_result_returns_result(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        self.assertEquals(crate.set_result(('wat?', 'some crazy message'))[0], 'unknown result')
        self.assertEquals(crate.result[0], 'unknown result')
