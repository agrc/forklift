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
        self.assertEqual(crate.source_name, 'sourceName')
        self.assertEqual(crate.source_workspace, 'blah')
        self.assertEqual(crate.destination_workspace, 'hello')
        self.assertEqual(crate.destination_name, 'blur')

    def test_destination_name_defaults_to_source(self):
        crate = Crate('sourceName', 'source', 'destination')
        self.assertEqual(crate.destination_name, crate.source_name)

    def test_bad_destination_name(self):
        crate = Crate('sourceName', 'source', 'destination_workspace', 'destination.Name')
        self.assertEqual(crate.result, (Crate.INVALID_DATA, 'Validation error with destination_name: destination.Name != destination_Name'))

    def test_good_destination_name(self):
        crate = Crate('sourceName', 'source', 'destination_workspace', 'destinationName')
        self.assertEqual(crate.result, (Crate.UNINITIALIZED, None))

    def test_set_result_with_valid_result_returns_result(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        self.assertEqual(crate.set_result((Crate.UPDATED, 'Yay!'))[0], Crate.UPDATED)
        self.assertEqual(crate.result[0], Crate.UPDATED)

    def test_set_result_with_invalid_result_returns_result(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        self.assertEqual(crate.set_result(('wat?', 'some crazy message'))[0], 'unknown result')
        self.assertEqual(crate.result[0], 'unknown result')

    def test_set_source_name_updates_source(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.set_source_name('oof')

        self.assertEqual(crate.source_name, 'oof')
        self.assertEqual(crate.source, join('bar', 'oof'))

    def test_set_source_name_updates_source_if_not_none(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.set_source_name(None)

        self.assertEqual(crate.source_name, 'foo')
        self.assertEqual(crate.source, join('bar', 'foo'))

    def test_crate_ctor_doesnt_alter_destination_name(self):
        source_name = 'name'
        source_workspace = 'does not matter'
        destination_workspace = env.scratchGDB
        destination_name = 'db.owner.name'

        x = Crate(source_name, source_workspace, destination_workspace, destination_name)

        self.assertEqual(x.destination_name, destination_name)

    def test_init_with_coordinate_system_as_number_becomes_spatial_reference(self):
        crate = Crate('foo', 'bar', 'baz', 'qux', 26912)
        self.assertEqual(crate.source_name, 'foo')
        self.assertEqual(crate.source_workspace, 'bar')
        self.assertEqual(crate.destination_workspace, 'baz')
        self.assertEqual(crate.destination_name, 'qux')
        self.assertIsInstance(crate.destination_coordinate_system, SpatialReference)

    def test_init_with_coordinate_system_does_not_change(self):
        crate = Crate('foo', 'bar', 'baz', 'qux', SpatialReference(26921))
        self.assertEqual(crate.source_name, 'foo')
        self.assertEqual(crate.source_workspace, 'bar')
        self.assertEqual(crate.destination_workspace, 'baz')
        self.assertEqual(crate.destination_name, 'qux')
        self.assertIsInstance(crate.destination_coordinate_system, SpatialReference)
