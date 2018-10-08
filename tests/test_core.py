#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
test_core.py
-----------------------------------------
Tests for the core.py module
'''

import inspect
import unittest
from os import path

import pytest
from mock import Mock, patch

import arcpy
from forklift import core, engine
from forklift.exceptions import ValidationException
from forklift.models import Changes, Crate

from . import mocks

current_folder = path.dirname(path.abspath(__file__))
suite_data_folder = path.join(current_folder, 'data', 'test_core')
update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
temp_gdb = path.join(current_folder, 'data', 'test.gdb')
test_folder = path.join(current_folder, 'data', 'test_create_folder')


def raise_validation_exception(crate):
    raise ValidationException()


def delete_if_arcpy_exists(data):
    if arcpy.Exists(data):
        arcpy.Delete_management(data)


def get_test_gdb():
    '''Returns a path to the fgdb for the calling test method.
    '''
    calling_method_name = inspect.stack()[1].function

    return path.join(suite_data_folder, '{}.gdb'.format(calling_method_name))


class CoreTests(unittest.TestCase):

    @classmethod
    def skip_if_no_local_sde(cls):
        if not cls.has_local_sde:
            raise pytest.skip('No test SDE dectected, skipping test')

    @classmethod
    def setUpClass(cls):
        delete_if_arcpy_exists(temp_gdb)
        delete_if_arcpy_exists(test_folder)
        engine.init()
        core.init(engine.log)

        #: check for local sde
        cls.has_local_sde = arcpy.Exists(path.join(update_tests_sde, 'ZipCodes'))

    def tearDown(self):
        delete_if_arcpy_exists(temp_gdb)

    def test_update_no_existing_destination(self):
        test_gdb = get_test_gdb()
        crate = Crate('ZipCodes', test_gdb, temp_gdb, 'ImNotHere')

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.CREATED)
        self.assertEqual(arcpy.Exists(crate.destination), True)

    def test_update_duplicate_features(self):
        test_gdb = get_test_gdb()
        arcpy.management.Copy(test_gdb, temp_gdb)
        crate = Crate('Duplicates', temp_gdb, temp_gdb, 'DuplicatesDest')

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination).getOutput(0), '4')

        #: remove feature
        with arcpy.da.UpdateCursor(crate.source, '*') as delete_cursor:
            for row in delete_cursor:
                delete_cursor.deleteRow()
                break

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination).getOutput(0), '3')

        #: change feature
        with arcpy.da.UpdateCursor(crate.source, ['TEST']) as update_cursor:
            for row in update_cursor:
                row[0] = 'change'
                update_cursor.updateRow(row)
                break

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.UPDATED_OR_CREATED_WITH_WARNINGS)
        self.assertEqual(arcpy.GetCount_management(crate.destination).getOutput(0), '3')

    def test_deleted_destination_between_updates(self):
        test_gdb = get_test_gdb()
        crate = Crate('ZipCodes', test_gdb, temp_gdb, 'ImNotHere')
        core.update(crate, lambda x: True)
        delete_if_arcpy_exists(crate.destination)

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.CREATED)
        self.assertEqual(arcpy.Exists(crate.destination), True)
        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 14)

    @patch('arcpy.Exists')
    def test_update_custom_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True
        crate = Crate('', '', '', describer=mocks.Describe)

        self.assertEqual(core.update(crate, raise_validation_exception)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_default_validation_that_fails(self, arcpy_exists):
        arcpy_exists.return_value = True
        core.check_schema = Mock(side_effect=ValidationException())

        def custom(crate):
            return NotImplemented

        crate = Crate('', '', '', describer=mocks.Describe)

        self.assertEqual(core.update(crate, custom)[0], Crate.INVALID_DATA)

    @patch('arcpy.Exists')
    def test_update_error(self, arcpy_exists):
        arcpy_exists.return_value = True

        crate = Crate('', '', '', describer=mocks.Describe)

        self.assertEqual(core.update(crate, lambda c: True)[0], Crate.UNHANDLED_EXCEPTION)

    def test_filter_shape_fields(self):
        self.assertEqual(core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_hash_custom_source_key_text(self):
        self.skip_if_no_local_sde()
        test_gdb = get_test_gdb()

        tbl = 'NO_OBJECTID_TEST'

        #: has changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, test_gdb, tbl)
        self.assertEqual(len(core._hash(crate).adds), 1)

        #: no changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, test_gdb, '{}_NO_CHANGES'.format(tbl))
        self.assertEqual(len(core._hash(crate).adds), 0)

    def test_hash_custom_source_key_float(self):
        self.skip_if_no_local_sde()
        test_gdb = get_test_gdb()

        tbl = 'FLOAT_ID'

        #: has changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, test_gdb, tbl)
        changes = core._hash(crate)
        self.assertEqual(len(changes.adds), 1)

    def test_hash_fgdb(self):
        test_gdb = get_test_gdb()

        def run_hash(fc1, fc2):
            return core._hash(Crate(fc1, test_gdb, test_gdb, fc2))

        zip_changes = run_hash('ZipCodes', 'ZipCodes_same')
        self.assertEqual(len(zip_changes.adds), 0)
        self.assertEqual(len(zip_changes._deletes), 0)
        self.assertEqual(len(run_hash('DNROilGasWells', 'DNROilGasWells_adds').adds), 4)
        line_changes = run_hash('Line', 'Line_same')
        self.assertEqual(len(line_changes.adds), 0)
        self.assertEqual(len(line_changes._deletes), 0)
        self.assertEqual(len(run_hash('NullShape', 'NullShape_missing_null').adds), 1)
        self.assertEqual(len(run_hash('Providers', 'Providers_adds').adds), 56)
        self.assertEqual(len(run_hash('NullDates', 'NullDates2').adds), 2)

    def test_hash_sde(self):
        self.skip_if_no_local_sde()

        test_gdb = get_test_gdb()

        def run(name):
            return core._hash(
                Crate(
                    name,
                    update_tests_sde,
                    test_gdb,
                    name,
                    destination_coordinate_system=arcpy.SpatialReference(3857),
                    geographic_transformation='NAD_1983_To_WGS_1984_5'
                )
            )

        self.assertEqual(len(run('Parcels_Morgan')._deletes), 2)

        #: different coordinate systems
        self.assertEqual(len(run('RuralTelcomBoundaries')._deletes), 1)

    def test_hash_shapefile(self):
        test_data_folder = path.join(suite_data_folder, 'test_hash_shapefile')
        fgdb = path.join(test_data_folder, 'data.gdb')
        crate = Crate('shapefile.shp', test_data_folder, fgdb, 'shapefile')
        changes = core._hash(crate)

        self.assertEqual(len(changes.adds), 1)

    def test_schema_changes(self):
        test_gdb = get_test_gdb()

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'FieldLength'))

        result = core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'ZipCodes'))
        self.assertEqual(result, True)

    def test_schema_changes_in_sde(self):
        self.skip_if_no_local_sde()
        test_gdb = get_test_gdb()

        result = core.check_schema(Crate('FieldTypeFloat', test_gdb, update_tests_sde, 'FieldTypeFloat'))
        self.assertEqual(result, True)

    def test_check_schema_ignore_length_for_all_except_text(self):
        self.skip_if_no_local_sde()

        test_gdb = get_test_gdb()

        # only worry about length on text fields
        result = core.check_schema(Crate(r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells', update_tests_sde, test_gdb, 'DNROilGasWells'))
        self.assertEqual(result, True)

    def test_check_schema_no_objectid_in_source(self):
        self.skip_if_no_local_sde()

        test_gdb = get_test_gdb()

        result = core.check_schema(Crate('UPDATE_TESTS.dbo.NO_OBJECTID_TEST', update_tests_sde, test_gdb, r'NO_OBJECTID_TEST'))
        self.assertEqual(result, True)

    def test_check_schema_match(self):
        test_gdb = get_test_gdb()

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldLength', test_gdb, test_gdb, 'FieldLength2'))

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldType', test_gdb, test_gdb, 'FieldType2'))

        self.assertTrue(core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'ZipCodes2')))

    def test_move_data_table(self):
        self.skip_if_no_local_sde()

        crate = Crate('Providers', update_tests_sde, temp_gdb)  #: table

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 57)

    def test_move_data_feature_class(self):
        self.skip_if_no_local_sde()

        crate = Crate('DNROilGasWells', update_tests_sde, temp_gdb)  #: feature class

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 5)

    def test_move_data_no_objectid(self):
        self.skip_if_no_local_sde()

        crate = Crate('NO_OBJECTID_TEST', update_tests_sde, temp_gdb)

        core.update(crate, lambda x: True)

        with arcpy.da.SearchCursor(crate.destination, '*') as cur:
            for row in cur:
                self.assertEqual('this is   ', row[1])
                break

    def test_move_data_skip_empty_geometry(self):
        test_gdb = get_test_gdb()

        empty_points = 'EmptyPointTest'

        crate = Crate(empty_points, test_gdb, temp_gdb)

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 4)

    def test_create_destination_data_feature_class(self):
        test_gdb = get_test_gdb()

        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        fc_crate = Crate('DNROilGasWells', test_gdb, temp_gdb)
        core._create_destination_data(fc_crate)
        self.assertTrue(arcpy.Exists(fc_crate.destination))

    def test_create_destination_data_table(self):
        test_gdb = get_test_gdb()

        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        tbl_crate = Crate('Providers', test_gdb, temp_gdb)
        core._create_destination_data(tbl_crate)
        self.assertTrue(arcpy.Exists(tbl_crate.destination))

    def test_create_destination_data_reproject(self):
        test_gdb = get_test_gdb()

        arcpy.CreateFileGDB_management(path.join(current_folder, 'data'), 'test.gdb')

        spatial_reference = arcpy.SpatialReference(3857)
        fc_crate = Crate(
            'DNROilGasWells', test_gdb, temp_gdb, destination_coordinate_system=spatial_reference, geographic_transformation='NAD_1983_To_WGS_1984_5'
        )
        core._create_destination_data(fc_crate)
        self.assertTrue(arcpy.Exists(fc_crate.destination))
        self.assertEqual(arcpy.Describe(fc_crate.destination).spatialReference.name, spatial_reference.name)

    @patch('arcpy.CreateFileGDB_management', wraps=arcpy.CreateFileGDB_management)
    def test_create_destination_data_workspace(self, create_mock):
        test_gdb = get_test_gdb()

        #: file geodatabase
        crate = Crate('DNROilGasWells', test_gdb, temp_gdb)
        core._create_destination_data(crate)

        create_mock.assert_called_once()

    def test_create_destination_data_raises(self):
        test_gdb = get_test_gdb()

        #: non-file geodatabase
        crate = Crate('DNROilGasWells', test_gdb, test_folder, 'test.shp')

        with self.assertRaises(Exception):
            core._create_destination_data(crate)

        delete_if_arcpy_exists(test_folder)

    def test_source_row_deleted(self):
        test_fgdb = get_test_gdb()
        arcpy.Copy_management(test_fgdb, temp_gdb)
        crate = Crate('RowDelete', temp_gdb, temp_gdb, 'RowDelete_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.UpdateCursor(crate.source, '*') as cur:
            for _ in cur:
                cur.deleteRow()
                break

        changes = core._hash(crate)

        #: all features hashes are invalid since we deleted the first row
        #: which changes the salt for all following rows
        self.assertEqual(len(changes.adds), 0)
        self.assertEqual(len(changes._deletes), 1)

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination)[0], '4')

    def test_source_row_added(self):
        test_fgdb = get_test_gdb()
        arcpy.Copy_management(test_fgdb, temp_gdb)
        crate = Crate('RowAdd', temp_gdb, temp_gdb, 'RowAdd_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.InsertCursor(crate.source, 'URL') as cur:
            cur.insertRow(('newrow',))

        changes = core._hash(crate)

        self.assertEqual(len(changes.adds), 1)
        self.assertEqual(len(changes._deletes), 0)

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination)[0], '6')

    def test_source_row_attribute_changed(self):
        test_fgdb = get_test_gdb()
        row_name = 'MALTA'
        arcpy.Copy_management(test_fgdb, temp_gdb)
        crate = Crate('AttributeChange', temp_gdb, temp_gdb, 'AttributeChange_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.UpdateCursor(crate.source, 'SYMBOL', 'NAME = \'{}\''.format(row_name)) as cur:
            for row in cur:
                row[0] = 99
                cur.updateRow(row)
                break

        changes = core._hash(crate)

        self.assertEqual(len(changes.adds), 1)

        self.assertEqual(len(changes._deletes), 1)

    def test_source_row_geometry_changed(self):
        test_fgdb = get_test_gdb()
        row_api = '4300311427'
        arcpy.Copy_management(test_fgdb, temp_gdb)
        crate = Crate('GeometryChange', temp_gdb, temp_gdb, 'GeometryChange_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.UpdateCursor(crate.source, 'Shape@XY', 'API = \'{}\''.format(row_api)) as cur:
            for row in cur:
                row[0] = (row[0][0] + 10, row[0][1] + 10)
                cur.updateRow(row)
                break

        changes = core._hash(crate)
        self.assertEqual(len(changes.adds), 1)

        self.assertEqual(len(changes._deletes), 1)

    def test_source_row_geometry_changed_to_none(self):
        test_fgdb = get_test_gdb()
        arcpy.Copy_management(test_fgdb, temp_gdb)
        crate = Crate('GeometryToNull', temp_gdb, temp_gdb, 'GeometryToNull_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.UpdateCursor(crate.source, 'Shape@XY') as cur:
            for row in cur:
                row[0] = None
                cur.updateRow(row)
                break

        changes = core._hash(crate)

        self.assertEqual(len(changes._deletes), 1)

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination)[0], '3')

    def test_check_counts(self):
        row_counts = get_test_gdb()

        #: matching
        crate = Crate('match', row_counts, row_counts, 'match')
        changes = Changes([])
        changes.total_rows = 3

        self.assertIsNone(core._check_counts(crate, changes))

        #: mismatching
        changes.total_rows = 2

        self.assertEquals(core._check_counts(crate, changes)[0], Crate.WARNING)

        #: empty
        crate = Crate('empty', row_counts, row_counts, 'empty')
        changes = Changes([])
        changes.total_rows = 0

        self.assertEqual(core._check_counts(crate, changes), (Crate.INVALID_DATA, 'Destination has zero rows!'))

    def test_mirror_fields(self):
        test_gdb = get_test_gdb()
        arcpy.management.CreateFileGDB(path.dirname(temp_gdb), path.basename(temp_gdb))
        destination = arcpy.management.CreateTable(temp_gdb, 'MirrorFieldsTable')

        core._mirror_fields(path.join(test_gdb, 'MirrorFields'), destination)

        fields = arcpy.da.Describe(destination)['fields']

        self.assertEqual(len(fields), 8)

        for field in fields:
            if field.name == 'TEST_TEXT':
                self.assertEqual(field.length, 25)
