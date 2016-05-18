#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
test_core.py
-----------------------------------------
Tests for the core.py module
'''

import arcpy
import os
import unittest
from forklift import core

currentFolder = os.path.dirname(os.path.abspath(__file__))
checkForChangesGDB = os.path.join(currentFolder, 'data', 'checkForChanges.gdb')
checkForChangesGDB2 = os.path.join(currentFolder, 'data', 'checkForChanges2.gdb')
updateTestsSDE = os.path.join(currentFolder, 'data', 'UPDATE_TESTS.sde')


def run_check_for_changes(fc1, fc2):
    f1 = os.path.join(checkForChangesGDB, fc1)
    f2 = os.path.join(checkForChangesGDB, fc2)
    return core.checkForChanges(f1, f2, False)


class CoreTests(unittest.TestCase):
    def test_checkForChanges(self):

        self.assertFalse(run_check_for_changes('ZipCodes', 'ZipCodes_same'))
        self.assertTrue(run_check_for_changes('ZipCodes', 'ZipCodes_geoMod'))
        self.assertTrue(run_check_for_changes('ZipCodes', 'ZipCodes_attMod'))
        self.assertTrue(run_check_for_changes('ZipCodes', 'ZipCodes_newFeature'))

    def test_check_for_changes_null_date_fields(self):
        self.assertTrue(run_check_for_changes('NullDates', 'NullDates2'))

    def test_filter_shape_fields(self):
        self.assertEquals(core.filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_no_updates(self):
        testGDB = os.path.join(currentFolder, 'Test.gdb')
        if arcpy.Exists(testGDB):
            arcpy.Delete_management(testGDB)
        arcpy.Copy_management(checkForChangesGDB2, testGDB)

        changes = core.updateFGDBfromSDE(testGDB, updateTestsSDE)[1]

        self.assertEquals(len(changes), 0)

    def test_update_tables(self):
        testGDB = os.path.join(currentFolder, 'Test.gdb')
        if arcpy.Exists(testGDB):
            arcpy.Delete_management(testGDB)
        arcpy.Copy_management(checkForChangesGDB, testGDB)

        changes = core.updateFGDBfromSDE(testGDB, updateTestsSDE)[1]

        self.assertEquals(changes[0], 'PROVIDERS')
