#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
test_core.py
-----------------------------------------
Tests for the core.py module
'''

import arcpy
import unittest
from forklift import core
from os import path
from nose import SkipTest


class CoreTests(unittest.TestCase):

    current_folder = path.dirname(path.abspath(__file__))
    check_for_changes_gdb = path.join(current_folder, 'data',
                                      'checkForChanges.gdb')
    check_for_changes_gdb2 = path.join(current_folder, 'data',
                                       'checkForChanges2.gdb')
    update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
    test_gdb = path.join(current_folder, 'data', 'test.gdb')

    def setUp(self):
        if arcpy.Exists(self.test_gdb):
            arcpy.Delete_management(self.test_gdb)

    def tearDown(self):
        if arcpy.Exists(self.test_gdb):
            arcpy.Delete_management(self.test_gdb)

    def check_for_local_sde(self):
        if not arcpy.Exists(path.join(self.update_tests_sde, 'ZipCodes')):
            raise SkipTest('No test SDE dectected, skipping test')

    def run_check_for_changes(self, fc1, fc2):
        f1 = path.join(self.check_for_changes_gdb, fc1)
        f2 = path.join(self.check_for_changes_gdb, fc2)

        return core._check_for_changes(f1, f2, False)

    def test_check_for_changes(self):
        self.assertFalse(self.run_check_for_changes('ZipCodes',
                                                    'ZipCodes_same'))
        self.assertTrue(self.run_check_for_changes('ZipCodes',
                                                   'ZipCodes_geoMod'))
        self.assertTrue(self.run_check_for_changes('ZipCodes',
                                                   'ZipCodes_attMod'))
        self.assertTrue(self.run_check_for_changes('ZipCodes',
                                                   'ZipCodes_newFeature'))

    def test_check_for_changes_null_date_fields(self):
        self.assertTrue(self.run_check_for_changes('NullDates', 'NullDates2'))

    def test_filter_shape_fields(self):
        self.assertEquals(
            core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_schema_changes(self):
        arcpy.Copy_management(self.check_for_changes_gdb, self.test_gdb)

        result = core._check_schema(
            path.join(self.test_gdb, 'ZipCodes'),
            path.join(self.check_for_changes_gdb, 'FieldLength'))
        self.assertEquals(result, False)

        result = core._check_schema(
            path.join(self.test_gdb, 'ZipCodes'),
            path.join(self.check_for_changes_gdb, 'ZipCodes'))
        self.assertEquals(result, True)

    def test_schema_changes_ignore_length_for_all_except_text(self):
        self.check_for_local_sde()

        # only worry about length on text fields
        result = core._check_schema(
            path.join(
                self.update_tests_sde,
                r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells'),
            path.join(self.check_for_changes_gdb, 'DNROilGasWells'))
        self.assertEquals(result, True)

    # def test_no_updates(self):
    #     self.check_for_local_sde()
    #     arcpy.Copy_management(self.check_for_changes_gdb2, self.test_gdb)
    #
    #     changes = core.update_fgdb_from_sde(self.test_gdb,
    #                                                 self.update_tests_sde)
    #
    #     self.assertEquals(len(changes), 0)

    # def test_updates(self):
    #     self.check_for_local_sde()
    #     arcpy.Copy_management(self.check_for_changes_gdb, self.test_gdb)
    #
    #     changes = core.update_fgdb_from_sde(self.test_gdb,
    #                                                 self.update_tests_sde)
    #
    #     self.assertEquals(changes[1], 'PROVIDERS')  # table
    #     self.assertEquals(changes[0], 'DNROILGASWELLS')  # within dataset

    def test_check_schema_match(self):
        self.assertEquals(
            core._check_schema(
                path.join(self.check_for_changes_gdb, 'FieldLength'),
                path.join(self.check_for_changes_gdb, 'FieldLength2')), False)

        self.assertEquals(
            core._check_schema(
                path.join(self.check_for_changes_gdb, 'FieldType'),
                path.join(self.check_for_changes_gdb, 'FieldType2')), False)

        self.assertEquals(
            core._check_schema(
                path.join(self.check_for_changes_gdb, 'ZipCodes'),
                path.join(self.check_for_changes_gdb2, 'ZipCodes')), True)
