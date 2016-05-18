#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
test_core.py
-----------------------------------------
Tests for the core.py module
'''

import arcpy
import unittest
from forklift.core import Core
from os import path


class CoreTests(unittest.TestCase):

    current_folder = path.dirname(path.abspath(__file__))
    check_for_changes_gdb = path.join(current_folder, 'data', 'checkForChanges.gdb')
    check_for_changes_gdb2 = path.join(current_folder, 'data', 'checkForChanges2.gdb')
    update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
    test_gdb = path.join(current_folder, 'data', 'test.gdb')

    def setUp(self):
        self.patient = Core()

        if arcpy.Exists(self.test_gdb):
            arcpy.Delete_management(self.test_gdb)

    def tearDown(self):
        if arcpy.Exists(self.test_gdb):
            arcpy.Delete_management(self.test_gdb)

    def run_check_for_changes(self, fc1, fc2):
        f1 = path.join(self.check_for_changes_gdb, fc1)
        f2 = path.join(self.check_for_changes_gdb, fc2)

        return self.patient.check_for_changes(f1, f2, False)

    def test_check_for_changes(self):
        self.assertFalse(self.run_check_for_changes('ZipCodes', 'ZipCodes_same'))
        self.assertTrue(self.run_check_for_changes('ZipCodes', 'ZipCodes_geoMod'))
        self.assertTrue(self.run_check_for_changes('ZipCodes', 'ZipCodes_attMod'))
        self.assertTrue(self.run_check_for_changes('ZipCodes', 'ZipCodes_newFeature'))

    def test_check_for_changes_null_date_fields(self):
        self.assertTrue(self.run_check_for_changes('NullDates', 'NullDates2'))

    def test_filter_shape_fields(self):
        self.assertEquals(self.patient._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_no_updates(self):
        arcpy.Copy_management(self.check_for_changes_gdb2, self.test_gdb)

        changes = self.patient.update_fgdb_from_sde(self.test_gdb, self.update_tests_sde)

        self.assertEquals(len(changes), 0)

    def test_update_tables(self):
        arcpy.Copy_management(self.check_for_changes_gdb, self.test_gdb)

        changes = self.patient.update_fgdb_from_sde(self.test_gdb, self.update_tests_sde)

        self.assertEquals(changes[0], 'PROVIDERS')
