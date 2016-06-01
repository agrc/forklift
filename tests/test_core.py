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
from forklift.models import Crate
from forklift.exceptions import ValidationException
from itertools import chain
from os import path
from nose import SkipTest
from mock import Mock, patch

current_folder = path.dirname(path.abspath(__file__))
check_for_changes_gdb = path.join(current_folder, 'data', 'checkForChanges.gdb')
check_for_changes_gdb2 = path.join(current_folder, 'data', 'checkForChanges2.gdb')
update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
test_gdb = path.join(current_folder, 'data', 'test.gdb')


def raise_validation_exception(crate):
    raise ValidationException()


class CoreTests(unittest.TestCase):

    def setUp(self):
        if arcpy.Exists(test_gdb):
            arcpy.Delete_management(test_gdb)

    def tearDown(self):
        if arcpy.Exists(test_gdb):
            arcpy.Delete_management(test_gdb)

    def check_for_local_sde(self):
        if not arcpy.Exists(path.join(update_tests_sde, 'ZipCodes')):
            raise SkipTest('No test SDE dectected, skipping test')

    def run_has_changes(self, fc1, fc2):
        return core._has_changes(Crate(fc1, check_for_changes_gdb, check_for_changes_gdb, fc2))

    def test_update_no_existing_destination(self):
        core._create_destination_data = Mock()

        crate = Crate('badname', 'nofolder', '')

        self.assertEquals(core.update(crate, lambda x: True)[0], Crate.CREATED)
        core._create_destination_data.assert_called_once()

    @patch('arcpy.Exists')
    def test_update_custom_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True

        crate = Crate('', '', '')

        self.assertEquals(core.update(crate, raise_validation_exception)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_default_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._check_schema = Mock(side_effect=ValidationException())

        def custom(crate):
            return NotImplemented

        crate = Crate('', '', '')

        self.assertEquals(core.update(crate, custom)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_successfully_updated(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(return_value=True)
        core._move_data = Mock()

        crate = Crate('', '', '')

        self.assertEquals(core.update(crate, lambda c: True)[0], Crate.UPDATED)

    @patch('arcpy.Exists')
    def test_update_no_changes(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(return_value=False)

        crate = Crate('', '', '')

        self.assertEquals(core.update(crate, lambda c: True)[0], Crate.NO_CHANGES)

    @patch('arcpy.Exists')
    def test_update_error(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(side_effect=Exception('error'))

        crate = Crate('', '', '')

        self.assertEquals(core.update(crate, lambda c: True), (Crate.UNHANDLED_EXCEPTION, 'error'))

    def test_has_changes(self):
        self.assertFalse(self.run_has_changes('ZipCodes', 'ZipCodes_same'))
        self.assertTrue(self.run_has_changes('ZipCodes', 'ZipCodes_geoMod'))
        self.assertTrue(self.run_has_changes('ZipCodes', 'ZipCodes_attMod'))
        self.assertTrue(self.run_has_changes('ZipCodes', 'ZipCodes_newFeature'))
        self.assertFalse(self.run_has_changes('DNROilGasWells', 'DNROilGasWells'))
        self.assertFalse(self.run_has_changes('Line', 'Line'))
        self.assertFalse(self.run_has_changes('NullShape', 'NullShape'))
        self.assertFalse(self.run_has_changes('Providers', 'Providers'))
        self.assertTrue(self.run_has_changes('NullDates', 'NullDates2'))

    def test_has_changes_null_date_fields(self):
        self.assertTrue(self.run_has_changes('NullDates', 'NullDates2'))

    def test_filter_shape_fields(self):
        self.assertEquals(core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_schema_changes(self):
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        result = core._check_schema(path.join(test_gdb, 'ZipCodes'), path.join(check_for_changes_gdb, 'FieldLength'))
        self.assertEquals(result, False)

        result = core._check_schema(path.join(test_gdb, 'ZipCodes'), path.join(check_for_changes_gdb, 'ZipCodes'))
        self.assertEquals(result, True)

    def test_check_schema_ignore_length_for_all_except_text(self):
        self.check_for_local_sde()

        # only worry about length on text fields
        result = core._check_schema(
            path.join(update_tests_sde, r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells'),
            path.join(check_for_changes_gdb, 'DNROilGasWells'))
        self.assertEquals(result, True)

    def test_move_data_table(self):
        self.check_for_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        crate = Crate('Providers', update_tests_sde, test_gdb)  #: table
        core._move_data(crate)

        self.assertEquals(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 57)

    def test_move_data_feature_class(self):
        self.check_for_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        crate = Crate('DNROilGasWells', update_tests_sde, test_gdb)  #: feature class
        core._move_data(crate)

        self.assertEquals(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 5)

    def test_check_schema_match(self):
        self.assertEquals(
            core._check_schema(
                path.join(check_for_changes_gdb, 'FieldLength'), path.join(check_for_changes_gdb, 'FieldLength2')),
            False)

        self.assertEquals(
            core._check_schema(
                path.join(check_for_changes_gdb, 'FieldType'), path.join(check_for_changes_gdb, 'FieldType2')), False)

        self.assertEquals(
            core._check_schema(
                path.join(check_for_changes_gdb, 'ZipCodes'), path.join(check_for_changes_gdb2, 'ZipCodes')), True)

    def test_create_destination_data_feature_class(self):
        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        fc_crate = Crate('DNROilGasWells', check_for_changes_gdb, test_gdb)
        core._create_destination_data(fc_crate)
        self.assertTrue(arcpy.Exists(fc_crate.destination))

    def test_create_destination_data_table(self):
        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        tbl_crate = Crate('Providers', check_for_changes_gdb, test_gdb)
        core._create_destination_data(tbl_crate)
        self.assertTrue(arcpy.Exists(tbl_crate.destination))

    def test_create_destination_data_reproject(self):
        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        spatial_reference = arcpy.SpatialReference(3857)
        fc_crate = Crate('DNROilGasWells',
                         check_for_changes_gdb,
                         test_gdb,
                         destination_coordinate_system=spatial_reference,
                         geographic_transformation='NAD_1983_To_WGS_1984_5')
        core._create_destination_data(fc_crate)
        self.assertTrue(arcpy.Exists(fc_crate.destination))
        self.assertEquals(arcpy.Describe(fc_crate.destination).spatialReference.name, spatial_reference.name)

    @patch('arcpy.da.Walk')
    def test_try_to_find_data_source_by_name_returns_and_updates_feature_name(self, walk):
        walk.return_value = chain([(None, None, ['db.owner.Counties'])])

        crate = Crate(source_name='Counties',
                      source_workspace='Database Connections\\something.sde',
                      destination_workspace='c:\\temp\\something.gdb',
                      destination_name='Counties')

        result = core._try_to_find_data_source_by_name(crate)
        ok = result[0]
        name = result[1]

        self.assertTrue(ok)
        self.assertEqual(name, 'db.owner.Counties')
        self.assertEqual(crate.source_name, name)
        self.assertEqual(crate.destination_name, 'Counties')
        self.assertEqual(crate.source, path.join(crate.source_workspace, crate.source_name))

    def test_try_to_find_data_source_by_name_returns_None_if_not_sde(self):
        crate = Crate(source_name='something.shp',
                      source_workspace='c:\\temp',
                      destination_workspace='c:\\something.gdb',
                      destination_name='Counties')

        self.assertIsNone(core._try_to_find_data_source_by_name(crate)[0])

    @patch('arcpy.da.Walk')
    def test_try_to_find_data_source_by_name_returns_False_if_duplicate(self, walk):
        walk.return_value = chain([(None, None, ['db.owner.Counties', 'db.owner2.Counties'])])

        crate = Crate(source_name='duplicate',
                      source_workspace='Database Connections\\something.sde',
                      destination_workspace='c:\\something.gdb',
                      destination_name='Counties')

        self.assertFalse(core._try_to_find_data_source_by_name(crate)[0])

    @patch('arcpy.da.Walk')
    def test_try_to_find_data_source_by_name_filters_common_duplicates(self, walk):
        walk.return_value = chain([(None, None, ['db.owner.Counties', 'db.owner.duplicateCounties'])])

        crate = Crate(source_name='Counties',
                      source_workspace='Database Connections\\something.sde',
                      destination_workspace='c:\\something.gdb',
                      destination_name='Counties')

        result = core._try_to_find_data_source_by_name(crate)
        ok = result[0]
        name = result[1]

        self.assertTrue(ok)
        self.assertEqual(name, 'db.owner.Counties')
        self.assertEqual(crate.source_name, name)
        self.assertEqual(crate.destination_name, 'Counties')
        self.assertEqual(crate.source, path.join(crate.source_workspace, crate.source_name))
