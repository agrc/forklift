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
from pathlib import Path

import pytest
from mock import MagicMock, Mock, patch

import arcpy
from forklift import core, engine
from forklift.change_detection import ChangeDetection
from forklift.exceptions import ValidationException
from forklift.models import Changes, Crate

from . import mocks

CURRENT_FOLDER = path.dirname(path.abspath(__file__))
SUITE_DATA_FOLDER = path.join(CURRENT_FOLDER, 'data', 'test_core')
UPDATE_TESTS_SDE = path.join(CURRENT_FOLDER, 'data', 'UPDATE_TESTS.sde')
TEMP_GDB = path.join(CURRENT_FOLDER, 'data', 'test.gdb')


def raise_validation_exception(crate):
    raise ValidationException()


def delete_if_arcpy_exists(data):
    if arcpy.Exists(data):
        arcpy.Delete_management(data)


#: check for local sde
HAS_LOCAL_SDE = arcpy.Exists(path.join(UPDATE_TESTS_SDE, 'ZipCodes'))
def skip_if_no_local_sde():
    if not HAS_LOCAL_SDE:
        raise pytest.skip('No test SDE detected, skipping test')


CHANGE_DETECTION = ChangeDetection([], 'blah')


@pytest.fixture(scope='function', autouse=True)
def set_up_modules():
    delete_if_arcpy_exists(TEMP_GDB)
    engine.init()
    core.init(engine.log)

    yield

    delete_if_arcpy_exists(TEMP_GDB)


def test_update_no_existing_destination(test_gdb):
    crate = Crate('ZipCodes', test_gdb, TEMP_GDB, 'ImNotHere')

    assert core.update(crate, lambda x: True, CHANGE_DETECTION)[0] == Crate.CREATED
    assert arcpy.Exists(crate.destination) == True


def test_update_duplicate_features(test_gdb):
    arcpy.management.Copy(test_gdb, TEMP_GDB)
    crate = Crate('Duplicates', TEMP_GDB, TEMP_GDB, 'DuplicatesDest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert arcpy.GetCount_management(crate.destination).getOutput(0) == '4'

    #: remove feature
    with arcpy.da.UpdateCursor(crate.source, '*') as delete_cursor:
        for row in delete_cursor:
            delete_cursor.deleteRow()
            break

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert arcpy.GetCount_management(crate.destination).getOutput(0) == '3'

    #: change feature
    with arcpy.da.UpdateCursor(crate.source, ['TEST']) as update_cursor:
        for row in update_cursor:
            row[0] = 'change'
            update_cursor.updateRow(row)
            break

    assert core.update(crate, lambda x: True, CHANGE_DETECTION)[0] == Crate.UPDATED_OR_CREATED_WITH_WARNINGS
    assert arcpy.GetCount_management(crate.destination).getOutput(0) == '3'

def test_deleted_destination_between_updates(test_gdb):
    crate = Crate('ZipCodes', test_gdb, TEMP_GDB, 'ImNotHere')
    core.update(crate, lambda x: True, CHANGE_DETECTION)
    delete_if_arcpy_exists(crate.destination)

    assert core.update(crate, lambda x: True, CHANGE_DETECTION)[0] == Crate.CREATED
    assert arcpy.Exists(crate.destination) == True
    assert int(arcpy.GetCount_management(crate.destination).getOutput(0)) == 14

@patch('arcpy.Exists')
def test_update_custom_validation_that_fails(arcpy_exists):
    arcpy_exists.return_value = True
    crate = Crate('', '', '', describer=mocks.Describe)

    assert core.update(crate, raise_validation_exception, CHANGE_DETECTION)[0] == Crate.INVALID_DATA

@patch('arcpy.Exists')
@patch('forklift.core.check_schema', Mock(side_effect=ValidationException()))
def test_update_default_validation_that_fails(arcpy_exists):
    arcpy_exists.return_value = True

    def custom(crate):
        return NotImplemented

    crate = Crate('', '', '', describer=mocks.Describe)

    assert core.update(crate, custom, CHANGE_DETECTION)[0] == Crate.INVALID_DATA

@patch('arcpy.Exists')
def test_update_error(arcpy_exists):
    arcpy_exists.return_value = True

    crate = Crate('', '', '', describer=mocks.Describe)

    assert core.update(crate, lambda c: True, CHANGE_DETECTION)[0] == Crate.UNHANDLED_EXCEPTION

def test_update_new_dataset_with_change_detection(test_gdb):
    change_detection = ChangeDetection([], 'blah')
    change_detection.has_table = MagicMock(name='has_table', return_value=True)
    change_detection.has_changed = MagicMock(name='has_changed', return_value=False)

    crate = Crate('Counties', test_gdb, test_gdb, 'Counties_Destination')

    core.update(crate, lambda c: True, change_detection)

    source_count = arcpy.management.GetCount(str(Path(test_gdb) / 'Counties'))[0]
    destination_count = arcpy.management.GetCount(str(Path(test_gdb) / 'Counties_Destination'))[0]

    assert source_count == destination_count

def test_filter_shape_fields():
    assert core._filter_fields(['shape', 'test', 'Shape_length', 'Global_ID']) == ['test']

def test_hash_custom_source_key_text(test_gdb):
    skip_if_no_local_sde()

    tbl = 'NO_OBJECTID_TEST'

    #: has changes
    crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), UPDATE_TESTS_SDE, test_gdb, tbl)
    assert len(core._hash(crate).adds) == 1

    #: no changes
    crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), UPDATE_TESTS_SDE, test_gdb, '{}_NO_CHANGES'.format(tbl))
    assert len(core._hash(crate).adds) == 0

def test_hash_custom_source_key_float(test_gdb):
    skip_if_no_local_sde()

    tbl = 'FLOAT_ID'

    #: has changes
    crate = Crate('UPDATE_TESTS.dbo.{}'.format(tbl), UPDATE_TESTS_SDE, test_gdb, tbl)
    changes = core._hash(crate)
    assert len(changes.adds) == 1

def test_hash_fgdb(test_gdb):

    def run_hash(fc1, fc2):
        return core._hash(Crate(fc1, test_gdb, test_gdb, fc2))

    zip_changes = run_hash('ZipCodes', 'ZipCodes_same')
    assert len(zip_changes.adds) == 0
    assert len(zip_changes._deletes) == 0
    assert len(run_hash('DNROilGasWells', 'DNROilGasWells_adds').adds) == 4
    line_changes = run_hash('Line', 'Line_same')
    assert len(line_changes.adds) == 0
    assert len(line_changes._deletes) == 0
    assert len(run_hash('NullShape', 'NullShape_missing_null').adds) == 1
    assert len(run_hash('Providers', 'Providers_adds').adds) == 56
    assert len(run_hash('NullDates', 'NullDates2').adds) == 2

def test_hash_sde(test_gdb):
    skip_if_no_local_sde()


    def run(name):
        return core._hash(
            Crate(
                name,
                UPDATE_TESTS_SDE,
                test_gdb,
                name,
                destination_coordinate_system=arcpy.SpatialReference(3857),
                geographic_transformation='NAD_1983_To_WGS_1984_5'
            )
        )

    assert len(run('Parcels_Morgan')._deletes) == 2

    #: different coordinate systems
    assert len(run('RuralTelcomBoundaries')._deletes) == 1

def test_hash_shapefile():
    test_data_folder = path.join(SUITE_DATA_FOLDER, 'test_hash_shapefile')
    fgdb = path.join(test_data_folder, 'data.gdb')
    crate = Crate('shapefile.shp', test_data_folder, fgdb, 'shapefile')
    changes = core._hash(crate)

    assert len(changes.adds) == 1

def test_schema_changes(test_gdb):

    with pytest.raises(ValidationException):
        core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'FieldLength'))

    result = core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'ZipCodes'))
    assert result == True

def test_schema_changes_in_sde(test_gdb):
    skip_if_no_local_sde()

    result = core.check_schema(Crate('FieldTypeFloat', test_gdb, UPDATE_TESTS_SDE, 'FieldTypeFloat'))
    assert result == True

def test_check_schema_ignore_length_for_all_except_text(test_gdb):
    skip_if_no_local_sde()


    # only worry about length on text fields
    result = core.check_schema(Crate(r'UPDATE_TESTS.DBO.Hello\UPDATE_TESTS.DBO.DNROilGasWells', UPDATE_TESTS_SDE, test_gdb, 'DNROilGasWells'))
    assert result == True

def test_check_schema_no_objectid_in_source(test_gdb):
    skip_if_no_local_sde()


    result = core.check_schema(Crate('UPDATE_TESTS.dbo.NO_OBJECTID_TEST', UPDATE_TESTS_SDE, test_gdb, r'NO_OBJECTID_TEST'))
    assert result == True

def test_check_schema_match(test_gdb):

    with pytest.raises(ValidationException):
        core.check_schema(Crate('FieldLength', test_gdb, test_gdb, 'FieldLength2'))

    with pytest.raises(ValidationException):
        core.check_schema(Crate('FieldType', test_gdb, test_gdb, 'FieldType2'))

    assert core.check_schema(Crate('ZipCodes', test_gdb, test_gdb, 'ZipCodes2')) == True


def test_move_data_table():
    skip_if_no_local_sde()

    crate = Crate('Providers', UPDATE_TESTS_SDE, TEMP_GDB)  #: table

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert int(arcpy.GetCount_management(crate.destination).getOutput(0)) == 57

def test_move_data_feature_class():
    skip_if_no_local_sde()

    crate = Crate('DNROilGasWells', UPDATE_TESTS_SDE, TEMP_GDB)  #: feature class

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert int(arcpy.GetCount_management(crate.destination).getOutput(0)) == 5

def test_move_data_no_objectid():
    skip_if_no_local_sde()

    crate = Crate('NO_OBJECTID_TEST', UPDATE_TESTS_SDE, TEMP_GDB)

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    with arcpy.da.SearchCursor(crate.destination, '*') as cur:
        for row in cur:
            assert 'this is   ' == row[1]
            break

def test_move_data_skip_empty_geometry(test_gdb):

    empty_points = 'EmptyPointTest'

    crate = Crate(empty_points, test_gdb, TEMP_GDB)

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert int(arcpy.GetCount_management(crate.destination).getOutput(0)) == 4

def test_create_destination_data_feature_class(test_gdb):

    arcpy.CreateFileGDB_management(path.join(CURRENT_FOLDER, 'data'), 'test.gdb')

    fc_crate = Crate('DNROilGasWells', test_gdb, TEMP_GDB)
    core._create_destination_data(fc_crate)
    assert arcpy.Exists(fc_crate.destination) == True

def test_create_destination_data_table(test_gdb):

    arcpy.CreateFileGDB_management(path.join(CURRENT_FOLDER, 'data'), 'test.gdb')

    tbl_crate = Crate('Providers', test_gdb, TEMP_GDB)
    core._create_destination_data(tbl_crate)
    assert arcpy.Exists(tbl_crate.destination) == True

def test_create_destination_data_reproject(test_gdb):

    arcpy.CreateFileGDB_management(path.join(CURRENT_FOLDER, 'data'), 'test.gdb')

    spatial_reference = arcpy.SpatialReference(3857)
    fc_crate = Crate(
        'DNROilGasWells', test_gdb, TEMP_GDB, destination_coordinate_system=spatial_reference, geographic_transformation='NAD_1983_To_WGS_1984_5'
    )
    core._create_destination_data(fc_crate)
    assert arcpy.Exists(fc_crate.destination) == True
    assert arcpy.Describe(fc_crate.destination).spatialReference.name == spatial_reference.name

@patch('arcpy.CreateFileGDB_management', wraps=arcpy.CreateFileGDB_management)
def test_create_destination_data_workspace(create_mock, test_gdb):

    #: file geodatabase
    crate = Crate('DNROilGasWells', test_gdb, TEMP_GDB)
    core._create_destination_data(crate)

    create_mock.assert_called_once()

def test_create_destination_data_raises(test_gdb, tmpdir):

    #: non-file geodatabase
    crate = Crate('DNROilGasWells', test_gdb, str(tmpdir), 'test.shp')

    with pytest.raises(Exception):
        core._create_destination_data(crate)

def test_source_row_deleted(test_gdb):
    arcpy.Copy_management(test_gdb, TEMP_GDB)
    crate = Crate('RowDelete', TEMP_GDB, TEMP_GDB, 'RowDelete_Dest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)
    with arcpy.da.UpdateCursor(crate.source, '*') as cur:
        for _ in cur:
            cur.deleteRow()
            break

    changes = core._hash(crate)

    #: all features hashes are invalid since we deleted the first row
    #: which changes the salt for all following rows
    assert len(changes.adds) == 0
    assert len(changes._deletes) == 1

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert arcpy.GetCount_management(crate.destination)[0] == '4'

def test_source_row_added(test_gdb):
    arcpy.Copy_management(test_gdb, TEMP_GDB)
    crate = Crate('RowAdd', TEMP_GDB, TEMP_GDB, 'RowAdd_Dest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)
    with arcpy.da.InsertCursor(crate.source, 'URL') as cur:
        cur.insertRow(('newrow',))

    changes = core._hash(crate)

    assert len(changes.adds) == 1
    assert len(changes._deletes) == 0

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert arcpy.GetCount_management(crate.destination)[0] == '6'

def test_source_row_attribute_changed(test_gdb):
    row_name = 'MALTA'
    arcpy.Copy_management(test_gdb, TEMP_GDB)
    crate = Crate('AttributeChange', TEMP_GDB, TEMP_GDB, 'AttributeChange_Dest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)
    with arcpy.da.UpdateCursor(crate.source, 'SYMBOL', 'NAME = \'{}\''.format(row_name)) as cur:
        for row in cur:
            row[0] = 99
            cur.updateRow(row)
            break

    changes = core._hash(crate)

    assert len(changes.adds) == 1

    assert len(changes._deletes) == 1

def test_source_row_geometry_changed(test_gdb):
    row_api = '4300311427'
    arcpy.Copy_management(test_gdb, TEMP_GDB)
    crate = Crate('GeometryChange', TEMP_GDB, TEMP_GDB, 'GeometryChange_Dest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)
    with arcpy.da.UpdateCursor(crate.source, 'Shape@XY', 'API = \'{}\''.format(row_api)) as cur:
        for row in cur:
            row[0] = (row[0][0] + 10, row[0][1] + 10)
            cur.updateRow(row)
            break

    changes = core._hash(crate)
    assert len(changes.adds) == 1

    assert len(changes._deletes) == 1

def test_source_row_geometry_changed_to_none(test_gdb):
    arcpy.Copy_management(test_gdb, TEMP_GDB)
    crate = Crate('GeometryToNull', TEMP_GDB, TEMP_GDB, 'GeometryToNull_Dest')

    core.update(crate, lambda x: True, CHANGE_DETECTION)
    with arcpy.da.UpdateCursor(crate.source, 'Shape@XY') as cur:
        for row in cur:
            row[0] = None
            cur.updateRow(row)
            break

    changes = core._hash(crate)

    assert len(changes._deletes) == 1

    core.update(crate, lambda x: True, CHANGE_DETECTION)

    assert arcpy.GetCount_management(crate.destination)[0] == '3'

def test_check_counts(test_gdb):
    #: matching
    crate = Crate('match', test_gdb, test_gdb, 'match')
    changes = Changes([])
    changes.total_rows = 3

    assert core._check_counts(crate, changes) == None

    #: mismatching
    changes.total_rows = 2

    assert core._check_counts(crate, changes)[0] == Crate.WARNING

    #: empty
    crate = Crate('empty', test_gdb, test_gdb, 'empty')
    changes = Changes([])
    changes.total_rows = 0

    assert core._check_counts(crate, changes), (Crate.INVALID_DATA == 'Destination has zero rows!')

def test_mirror_fields(test_gdb):
    arcpy.management.CreateFileGDB(path.dirname(TEMP_GDB), path.basename(TEMP_GDB))
    destination = arcpy.management.CreateTable(TEMP_GDB, 'MirrorFieldsTable')

    core._mirror_fields(path.join(test_gdb, 'MirrorFields'), destination)

    fields = arcpy.da.Describe(destination)['fields']

    assert len(fields) == 8

    for field in fields:
        if field.name == 'TEST_TEXT':
            assert field.length == 25


def test_schema_changes_field_case_differences(test_gdb):
    with pytest.raises(ValidationException):
        core.check_schema(Crate('lower', test_gdb, test_gdb, 'UPPER'))


def test_schema_ignore_non_standard_shape_length_fields(test_gdb):
    result = core.check_schema(Crate('DirectionalSurveyHeaderSource', test_gdb, test_gdb, 'DirectionalSurveyHeaderDestination'))

    assert result
