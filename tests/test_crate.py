#!/usr/bin/env python
# * coding: utf8 *
'''
test_crate.py

A module for testing crate.py
'''

import unittest
from arcpy import env, SpatialReference
from forklift.models import Crate
from os.path import join


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

    def test_set_source_name_updates_source(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.set_source_name('oof')

        self.assertEquals(crate.source_name, 'oof')
        self.assertEquals(crate.source, join('bar', 'oof'))

    def test_set_source_name_updates_source_if_not_none(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.set_source_name(None)

        self.assertEquals(crate.source_name, 'foo')
        self.assertEquals(crate.source, join('bar', 'foo'))

    def test_crate_ctor_replaces_period_with___(self):
        source_name = 'db.owner.name'
        source_workspace = 'does not matter'
        destination_workspace = env.scratchGDB

        x = Crate(source_name, source_workspace, destination_workspace)

        self.assertEquals(x.destination_name, 'db_owner_name')

    def test_crate_ctor_prepends_T_if_name_starts_with_non_alpha(self):
        source_name = '123456789'
        source_workspace = 'does not matter'
        destination_workspace = env.scratchGDB

        x = Crate(source_name, source_workspace, destination_workspace)
        # : arcpy seems to put a T infront of this to make it valid?
        self.assertEquals(x.destination_name, 'T' + source_name)

        source_name = '*special_character'
        x = Crate(source_name, source_workspace, destination_workspace)
        self.assertEquals(x.destination_name, 'T_special_character')

        source_name = '%special_character'
        x = Crate(source_name, source_workspace, destination_workspace)
        self.assertEquals(x.destination_name, 'T_special_character')

    def test_crate_ctor_replaces_space_with___(self):
        source_name = 'space in name'
        source_workspace = 'does not matter'
        destination_workspace = env.scratchGDB

        x = Crate(source_name, source_workspace, destination_workspace)
        self.assertEquals(x.destination_name, 'space_in_name')

    def test_init_with_coordinate_system_as_number_becomes_spatial_reference(self):
        crate = Crate('foo', 'bar', 'baz', 'qux', 26912)
        self.assertEquals(crate.source_name, 'foo')
        self.assertEquals(crate.source_workspace, 'bar')
        self.assertEquals(crate.destination_workspace, 'baz')
        self.assertEquals(crate.destination_name, 'qux')
        self.assertIsInstance(crate.destination_coordinate_system, SpatialReference)

    def test_init_with_coordinate_system_does_not_change(self):
        crate = Crate('foo', 'bar', 'baz', 'qux', SpatialReference(26921))
        self.assertEquals(crate.source_name, 'foo')
        self.assertEquals(crate.source_workspace, 'bar')
        self.assertEquals(crate.destination_workspace, 'baz')
        self.assertEquals(crate.destination_name, 'qux')
        self.assertIsInstance(crate.destination_coordinate_system, SpatialReference)
