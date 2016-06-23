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
from mock import Mock
from mock import patch

current_folder = path.dirname(path.abspath(__file__))
check_for_changes_gdb = path.join(current_folder, 'data', 'checkForChanges.gdb')
check_for_changes_gdb2 = path.join(current_folder, 'data', 'checkForChanges2.gdb')
update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
test_gdb = path.join(current_folder, 'data', 'test.gdb')
test_folder = path.join(current_folder, 'data', 'test_create_folder')


def raise_validation_exception(crate):
    raise ValidationException()


def delete_if_exists(data):
    if arcpy.Exists(data):
        arcpy.Delete_management(data)


def skip_if_no_local_sde():
    if not arcpy.Exists(path.join(update_tests_sde, 'ZipCodes')):
        raise SkipTest('No test SDE dectected, skipping test')


class CoreTests(unittest.TestCase):
    def setUp(self):
        delete_if_exists(test_gdb)
        delete_if_exists(test_folder)

    def tearDown(self):
        delete_if_exists(test_gdb)
        delete_if_exists(test_folder)

    def test_update_no_existing_destination(self):
        core._create_destination_data = Mock()

        crate = Crate('badname', 'nofolder', '')

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.CREATED)
        core._create_destination_data.assert_called_once()

    @patch('arcpy.Exists')
    def test_update_custom_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True

        crate = Crate('', '', '')

        self.assertEqual(core.update(crate, raise_validation_exception)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_default_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True
        core.check_schema = Mock(side_effect=ValidationException())

        def custom(crate):
            return NotImplemented

        crate = Crate('', '', '')

        self.assertEqual(core.update(crate, custom)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_successfully_updated(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(return_value=True)
        core._move_data = Mock()

        crate = Crate('', '', '')

        self.assertEqual(core.update(crate, lambda c: True)[0], Crate.UPDATED)

    @patch('arcpy.Exists')
    def test_update_error(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(side_effect=Exception('error'))

        crate = Crate('', '', '')

        self.assertEqual(core.update(crate, lambda c: True), (Crate.UNHANDLED_EXCEPTION, 'error'))

    def test_filter_shape_fields(self):
        self.assertEqual(core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def run_has_changes(self, fc1, fc2):
        return core._has_changes(Crate(fc1, check_for_changes_gdb, check_for_changes_gdb, fc2))

    def test_has_changes_no_OBJECTID_in_source(self):
        skip_if_no_local_sde()

        tbl = 'NO_OBJECTID_TEST'

        #: has changes
        self.assertTrue(core._has_changes(Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, check_for_changes_gdb, tbl)))

        #: no changes
        self.assertFalse(core._has_changes(Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, check_for_changes_gdb, '{}_NO_CHANGES'.format(tbl))))

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

    def test_has_changes_shapefile(self):
        self.assertFalse(core._has_changes(Crate('shapefile.shp', path.join(current_folder, 'data'), check_for_changes_gdb, 'shapefile')))

    def test_has_changes_null_date_fields(self):
        self.assertTrue(self.run_has_changes('NullDates', 'NullDates2'))

    @patch('arcpy.Exists')
    def test_update_no_changes(self, arcpy_exists):
        arcpy_exists.return_value = True
        core._has_changes = Mock(return_value=False)

        crate = Crate('', '', '')

        self.assertEqual(core.update(crate, lambda c: True)[0], Crate.NO_CHANGES)

    def test_schema_changes(self):
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('ZipCodes', test_gdb, check_for_changes_gdb, 'FieldLength'))

        result = core.check_schema(Crate('ZipCodes', test_gdb, check_for_changes_gdb, 'ZipCodes'))
        self.assertEqual(result, True)

    def test_schema_changes_in_sde(self):
        skip_if_no_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        result = core.check_schema(Crate('FieldTypeFloat', test_gdb, update_tests_sde, 'FieldTypeFloat'))
        self.assertEqual(result, True)

    def test_check_schema_ignore_length_for_all_except_text(self):
        skip_if_no_local_sde()

        # only worry about length on text fields
        result = core.check_schema(Crate(r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells',
                                         update_tests_sde,
                                         check_for_changes_gdb,
                                         'DNROilGasWells'))
        self.assertEqual(result, True)

    def test_check_schema_no_objectid_in_source(self):
        skip_if_no_local_sde()

        result = core.check_schema(Crate('UPDATE_TESTS.dbo.NO_OBJECTID_TEST',
                                         update_tests_sde,
                                         check_for_changes_gdb,
                                         r'NO_OBJECTID_TEST'))
        self.assertEqual(result, True)

    def test_check_schema_match(self):
        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldLength', check_for_changes_gdb, check_for_changes_gdb, 'FieldLength2'))

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldType', check_for_changes_gdb, check_for_changes_gdb, 'FieldType2'))

        self.assertEqual(core.check_schema(Crate('ZipCodes', check_for_changes_gdb, check_for_changes_gdb2, 'ZipCodes')), True)

    def test_move_data_table(self):
        skip_if_no_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        crate = Crate('Providers', update_tests_sde, test_gdb)  #: table
        core._move_data(crate)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 57)

    def test_move_data_feature_class(self):
        skip_if_no_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        crate = Crate('DNROilGasWells', update_tests_sde, test_gdb)  #: feature class
        core._move_data(crate)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 5)

    def test_move_data_no_objectid(self):
        skip_if_no_local_sde()
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)

        crate = Crate('NO_OBJECTID_TEST', update_tests_sde, test_gdb)
        core._move_data(crate)

        with arcpy.da.SearchCursor(crate.destination, '*') as cur:
            row = cur.next()
            self.assertEqual('this is   ', row[1])

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
        self.assertEqual(arcpy.Describe(fc_crate.destination).spatialReference.name, spatial_reference.name)

    @patch('arcpy.CreateFileGDB_management', wraps=arcpy.CreateFileGDB_management)
    def test_create_destination_data_workspace(self, create_mock):
        #: file geodatabase
        crate = Crate('DNROilGasWells', check_for_changes_gdb, test_gdb)
        core._create_destination_data(crate)

        create_mock.assert_called_once()

    def test_create_destination_data_raises(self):
        #: non-file geodatabase
        crate = Crate('DNROilGasWells', check_for_changes_gdb, test_folder, 'test.shp')

        with self.assertRaises(Exception):
            core._create_destination_data(crate)

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
