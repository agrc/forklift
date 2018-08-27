#!/usr/bin/env python
# * coding: utf8 *
'''
test_crate.py

A module for testing crate.py
'''

import unittest
from os import path

import arcpy
from arcpy import SpatialReference, env
from forklift.models import Crate
from mock import patch
from nose import SkipTest
from xxhash import xxh64

current_folder = path.dirname(path.abspath(__file__))
check_for_changes_fgdb = path.join(current_folder, 'data', 'checkForChanges.gdb')
update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')


def skip_if_no_local_sde():
    if not arcpy.Exists(path.join(update_tests_sde, 'ZipCodes')):
        raise SkipTest('No test SDE dectected, skipping test')


class TestCrate(unittest.TestCase):

    def test_pass_all_values(self):
        crate = Crate('sourceName', 'blah', 'hello', 'blur')
        self.assertEqual(crate.source_name, 'sourceName')
        self.assertEqual(crate.source_workspace, 'blah')
        self.assertEqual(crate.destination_workspace, 'hello')
        self.assertEqual(crate.destination_name, 'blur')

    def test_destination_name_defaults_to_source(self):
        crate = Crate('DNROilGasWells', check_for_changes_fgdb, check_for_changes_fgdb)
        self.assertEqual(crate.destination_name, crate.source_name)

    def test_bad_destination_name(self):
        crate = Crate('DNROilGasWells', check_for_changes_fgdb, 'destination_workspace', 'destination.Name')
        self.assertEqual(crate.result, (Crate.INVALID_DATA, 'Validation error with destination_name: destination.Name != destination_Name'))

    def test_good_destination_name(self):
        crate = Crate('DNROilGasWells', check_for_changes_fgdb, check_for_changes_fgdb, 'destinationName')
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
        self.assertEqual(crate.source, path.join('bar', 'oof'))

    def test_set_source_name_updates_source_if_not_none(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.set_source_name(None)

        self.assertEqual(crate.source_name, 'foo')
        self.assertEqual(crate.source, path.join('bar', 'foo'))

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

    def test_create_name_is_combined_hash_and_table_four_values(self):
        destination_workspace = 'dw'
        destination_name = 'dn'
        crate = Crate('sourceName', 'source', destination_workspace, destination_name)

        hash = destination_name + '_' + xxh64(path.join(destination_workspace, destination_name)).hexdigest()

        self.assertEqual(crate.name, hash)

    def test_create_name_is_combined_hash_and_table_three_values(self):
        destination_workspace = 'dw'
        source_name = 'sn'
        crate = Crate(source_name, 'source', destination_workspace)

        hash = source_name + '_' + xxh64(path.join(destination_workspace, source_name)).hexdigest()

        self.assertEqual(crate.name, hash)

    @patch('arcpy.ListFeatureClasses')
    def test_try_to_find_data_source_by_name_returns_and_updates_feature_name(self, list_feature_classes):
        list_feature_classes.return_value = ['db.owner.Counties']

        crate = Crate(
            source_name='Counties',
            source_workspace='Database Connections\\something.sde',
            destination_workspace='c:\\temp\\something.gdb',
            destination_name='Counties')

        #: reset values because _try_to_find_data_source_by_name is called in the init
        crate.set_source_name('Counties')

        ok, name = crate._try_to_find_data_source_by_name()

        self.assertTrue(ok)
        self.assertEqual(name, 'db.owner.Counties')
        self.assertEqual(crate.source_name, name)
        self.assertEqual(crate.destination_name, 'Counties')
        self.assertEqual(crate.source, path.join(crate.source_workspace, crate.source_name))

    def test_try_to_find_data_source_by_name_returns_None_if_not_sde(self):
        crate = Crate(source_name='something.shp', source_workspace='c:\\temp', destination_workspace='c:\\something.gdb', destination_name='Counties')

        self.assertIsNone(crate._try_to_find_data_source_by_name()[0])

    @patch('arcpy.ListTables')
    def test_try_to_find_data_source_by_name_returns_False_if_duplicate(self, list_tables):
        list_tables.return_value = ['db.owner.Counties', 'db.owner2.Counties']

        crate = Crate(
            source_name='duplicate',
            source_workspace='Database Connections\\something.sde',
            destination_workspace='c:\\something.gdb',
            destination_name='Counties')

        self.assertFalse(crate._try_to_find_data_source_by_name()[0])

    @patch('arcpy.ListFeatureClasses')
    def test_try_to_find_data_source_by_name_filters_common_duplicates(self, list_feature_classes):
        list_feature_classes.return_value = ['db.owner.Counties', 'db.owner.duplicateCounties']

        crate = Crate(
            source_name='Counties',
            source_workspace='Database Connections\\something.sde',
            destination_workspace='c:\\something.gdb',
            destination_name='Counties')

        #: reset values because _try_to_find_data_source_by_name is called in the init
        crate.set_source_name('Counties')

        ok, name = crate._try_to_find_data_source_by_name()

        self.assertTrue(ok)
        self.assertEqual(name, 'db.owner.Counties')
        self.assertEqual(crate.source_name, name)
        self.assertEqual(crate.destination_name, 'Counties')
        self.assertEqual(crate.source, path.join(crate.source_workspace, crate.source_name))

    def test_get_report(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.result = (Crate.NO_CHANGES, None)

        self.assertIsNone(crate.get_report())

        msg = 'blah'
        crate.result = (Crate.CREATED, msg)

        self.assertEqual(crate.get_report()['crate_message'], msg)

        crate.result = (Crate.WARNING, msg)

        self.assertEqual(crate.get_report()['result'], Crate.WARNING)
        self.assertEqual(crate.get_report()['message_level'], 'warning')

        crate.result = (Crate.UNHANDLED_EXCEPTION, msg)
        self.assertEqual(crate.get_report()['message_level'], 'error')

        crate.result = (Crate.INVALID_DATA, msg)
        self.assertEqual(crate.get_report()['message_level'], 'error')

    def test_was_updated(self):
        crate = Crate('foo', 'bar', 'baz', 'goo')

        crate.result = (Crate.INVALID_DATA, None)
        self.assertFalse(crate.was_updated())

        crate.result = (Crate.WARNING, None)
        self.assertFalse(crate.was_updated())

        crate.result = (Crate.NO_CHANGES, None)
        self.assertFalse(crate.was_updated())

        crate.result = (Crate.UNHANDLED_EXCEPTION, None)
        self.assertFalse(crate.was_updated())

        crate.result = (Crate.UNINITIALIZED, None)
        self.assertFalse(crate.was_updated())

        crate.result = (Crate.CREATED, None)
        self.assertTrue(crate.was_updated())

        crate.result = (Crate.UPDATED, None)
        self.assertTrue(crate.was_updated())

        crate.result = (Crate.UPDATED_OR_CREATED_WITH_WARNINGS, None)
        self.assertTrue(crate.was_updated())
