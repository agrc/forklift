#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
test_core.py
-----------------------------------------
Tests for the core.py module
'''

import arcpy
from . import mocks
import unittest
from forklift import cli
from forklift import core
from forklift.models import Crate, Changes
from forklift.exceptions import ValidationException
from os import path
from nose import SkipTest
from mock import Mock
from mock import patch

current_folder = path.dirname(path.abspath(__file__))
check_for_changes_gdb = path.join(current_folder, 'data', 'checkForChanges.gdb')
duplicates_gdb = path.join(current_folder, 'data', 'Duplicates.gdb')
duplicates_gdb_copy = path.join(current_folder, 'data', 'DuplicatesCopy.gdb')
check_for_changes_gdb2 = path.join(current_folder, 'data', 'checkForChanges2.gdb')
update_tests_sde = path.join(current_folder, 'data', 'UPDATE_TESTS.sde')
test_gdb = path.join(current_folder, 'data', 'test.gdb')
test_folder = path.join(current_folder, 'data', 'test_create_folder')


def raise_validation_exception(crate):
    raise ValidationException()


def delete_if_arcpy_exists(data):
    if arcpy.Exists(data):
        arcpy.Delete_management(data)


def skip_if_no_local_sde():
    if not arcpy.Exists(path.join(update_tests_sde, 'ZipCodes')):
        raise SkipTest('No test SDE dectected, skipping test')


class CoreTests(unittest.TestCase):

    def setUp(self):
        delete_if_arcpy_exists(test_gdb)
        delete_if_arcpy_exists(test_folder)
        delete_if_arcpy_exists(duplicates_gdb_copy)
        cli.init()
        core.init(cli.log)

    def tearDown(self):
        delete_if_arcpy_exists(test_gdb)
        delete_if_arcpy_exists(test_folder)
        delete_if_arcpy_exists(duplicates_gdb_copy)
        delete_if_arcpy_exists(path.join(current_folder, 'config.json'))

    def test_update_no_existing_destination(self):
        crate = Crate('ZipCodes', check_for_changes_gdb, test_gdb, 'ImNotHere')

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.CREATED)
        self.assertEqual(arcpy.Exists(crate.destination), True)

    def test_update_duplicate_features(self):
        arcpy.Copy_management(duplicates_gdb, duplicates_gdb_copy)
        crate = Crate('Duplicates', duplicates_gdb_copy, test_gdb, 'DuplicatesDest')

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

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.UPDATED)
        self.assertEqual(arcpy.GetCount_management(crate.destination).getOutput(0), '3')

    def test_deleted_destination_between_updates(self):
        crate = Crate('ZipCodes', check_for_changes_gdb, test_gdb, 'ImNotHere')
        core.update(crate, lambda x: True)
        delete_if_arcpy_exists(crate.destination)

        self.assertEqual(core.update(crate, lambda x: True)[0], Crate.CREATED)
        self.assertEqual(arcpy.Exists(crate.destination), True)
        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 299)

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
        self.assertEqual(
            core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']), ['test'])

    def test_hash_custom_source_key_text(self):
        skip_if_no_local_sde()

        tbl = 'NO_OBJECTID_TEST'

        #: has changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, check_for_changes_gdb, tbl, source_primary_key='TEST')
        self.assertEqual(len(core._hash(crate).adds), 1)

        #: no changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, check_for_changes_gdb, '{}_NO_CHANGES'.format(tbl), source_primary_key='TEST')
        self.assertEqual(len(core._hash(crate).adds), 0)

    def test_hash_custom_source_key_float(self):
        skip_if_no_local_sde()

        tbl = 'FLOAT_ID'

        #: has changes
        crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), update_tests_sde, check_for_changes_gdb, tbl, source_primary_key='TEST')
        changes = core._hash(crate)
        self.assertEqual(len(changes.adds), 1)

    def test_hash_fgdb(self):
        def run_hash(fc1, fc2):
            return core._hash(Crate(fc1, check_for_changes_gdb, check_for_changes_gdb, fc2))

        self.assertEqual(len(run_hash('ZipCodes', 'ZipCodes_same').adds), 0)
        self.assertEqual(len(run_hash('ZipCodes', 'ZipCodes_same')._deletes), 0)
        self.assertEqual(len(run_hash('DNROilGasWells', 'DNROilGasWells_adds').adds), 4)
        self.assertEqual(len(run_hash('Line', 'Line_same').adds), 0)
        self.assertEqual(len(run_hash('Line', 'Line_same')._deletes), 0)
        self.assertEqual(len(run_hash('NullShape', 'NullShape_missing_null').adds), 1)
        self.assertEqual(len(run_hash('Providers', 'Providers_adds').adds), 56)
        self.assertEqual(len(run_hash('NullDates', 'NullDates2').adds), 2)

    def test_hash_sde(self):
        skip_if_no_local_sde()

        def run(name):
            return core._hash(
                Crate(
                    name,
                    update_tests_sde,
                    check_for_changes_gdb,
                    name + '_NEW',
                    destination_coordinate_system=arcpy.SpatialReference(3857),
                    geographic_transformation='NAD_1983_To_WGS_1984_5')
                )

        self.assertEqual(len(run('Parcels_Morgan')._deletes), 1)

        #: different coordinate systems
        self.assertEqual(len(run('RuralTelcomBoundaries')._deletes), 1)

    def test_hash_shapefile(self):
        data_folder = path.join(current_folder, 'data')
        crate = Crate('shapefile.shp', data_folder, check_for_changes_gdb, 'shapefile')
        changes = core._hash(crate)

        self.assertEqual(len(changes.adds), 1)

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
        result = core.check_schema(Crate(r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells', update_tests_sde, check_for_changes_gdb, 'DNROilGasWells'))
        self.assertEqual(result, True)

    def test_check_schema_no_objectid_in_source(self):
        skip_if_no_local_sde()

        result = core.check_schema(Crate('UPDATE_TESTS.dbo.NO_OBJECTID_TEST', update_tests_sde, check_for_changes_gdb, r'NO_OBJECTID_TEST'))
        self.assertEqual(result, True)

    def test_check_schema_match(self):
        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldLength', check_for_changes_gdb, check_for_changes_gdb, 'FieldLength2'))

        with self.assertRaises(ValidationException):
            core.check_schema(Crate('FieldType', check_for_changes_gdb, check_for_changes_gdb, 'FieldType2'))

        self.assertEqual(core.check_schema(Crate('ZipCodes', check_for_changes_gdb, check_for_changes_gdb2, 'ZipCodes')), True)

    def test_move_data_table(self):
        skip_if_no_local_sde()

        crate = Crate('Providers', update_tests_sde, test_gdb)  #: table

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 57)

    def test_move_data_feature_class(self):
        skip_if_no_local_sde()

        crate = Crate('DNROilGasWells', update_tests_sde, test_gdb)  #: feature class

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 5)

    def test_move_data_no_objectid(self):
        skip_if_no_local_sde()

        crate = Crate('NO_OBJECTID_TEST', update_tests_sde, test_gdb, source_primary_key='TEST')

        core.update(crate, lambda x: True)

        with arcpy.da.SearchCursor(crate.destination, '*') as cur:
            for row in cur:
                self.assertEqual('this is   ', row[1])
                break

    def test_move_data_skip_empty_geometry(self):
        empty_geometry_gdb = path.join(current_folder, 'data', 'EmptyGeometry.gdb')
        empty_points = 'EmptyPointTest'

        crate = Crate(empty_points, empty_geometry_gdb, test_gdb)

        core.update(crate, lambda x: True)

        self.assertEqual(int(arcpy.GetCount_management(crate.destination).getOutput(0)), 4)

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
        fc_crate = Crate(
            'DNROilGasWells',
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

    def test_source_row_deleted(self):
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)
        crate = Crate('RowDelete', test_gdb, test_gdb, 'RowDelete_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.UpdateCursor(crate.source, '*') as cur:
            for row in cur:
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
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)
        crate = Crate('RowAdd', test_gdb, test_gdb, 'RowAdd_Dest')

        core.update(crate, lambda x: True)
        with arcpy.da.InsertCursor(crate.source, 'URL') as cur:
            cur.insertRow(('newrow',))

        changes = core._hash(crate)

        self.assertEqual(len(changes.adds), 1)
        self.assertEqual(len(changes._deletes), 0)

        core.update(crate, lambda x: True)

        self.assertEqual(arcpy.GetCount_management(crate.destination)[0], '6')

    def test_source_row_attribute_changed(self):
        row_name = 'MALTA'
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)
        crate = Crate('AttributeChange', test_gdb, test_gdb, 'AttributeChange_Dest')

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
        row_api = '4300311427'
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)
        crate = Crate('GeometryChange', test_gdb, test_gdb, 'GeometryChange_Dest')

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
        arcpy.Copy_management(check_for_changes_gdb, test_gdb)
        crate = Crate('GeometryToNull', test_gdb, test_gdb, 'GeometryToNull_Dest')

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
        row_counts = path.join(current_folder, 'data', 'RowCounts.gdb')

        #: matching
        crate = Crate('match', row_counts, row_counts, 'match')
        changes = Changes([])
        changes.total_rows = 3

        self.assertTrue(core._check_counts(crate, changes)[0])

        #: mismatching
        changes.total_rows = 2

        self.assertFalse(core._check_counts(crate, changes)[0])

    def test_mirror_fields(self):
        arcpy.management.CreateFileGDB(path.dirname(test_gdb), path.basename(test_gdb))
        destination = arcpy.management.CreateTable(test_gdb, 'MirrorFieldsTable')

        core._mirror_fields(path.join(check_for_changes_gdb, 'MirrorFields'), destination)

        fields = arcpy.da.Describe(destination)['fields']

        self.assertEqual(len(fields), 8)

        for field in fields:
            if field.name == 'TEST_TEXT':
                self.assertEqual(field.length, 25)
