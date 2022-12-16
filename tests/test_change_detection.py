#!/usr/bin/env python
# * coding: utf8 *
'''
test_change_detection.py
a module containing tests for the change detection module
'''
import logging
from pathlib import Path

import arcpy
from pytest import raises

from forklift import core
from forklift.change_detection import (ChangeDetection, _get_hashes,
                                       hash_field, table_name_field)
from forklift.models import Crate

test_data_folder = str(Path(__file__).parent / 'data')

def test_has_table(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    change_detection = ChangeDetection(['ChangeDetection'], test_gdb, hash_table=hash_table)

    assert change_detection.has_table('UPDATE_TESTS.dbo.counties')
    assert change_detection.has_table('bad table name') == False

def test_has_changed(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    change_detection = ChangeDetection(['ChangeDetection'], test_gdb, hash_table=hash_table)

    assert change_detection.has_changed('UPDATE_TESTS.dbo.counties') == False
    assert change_detection.has_changed('UPDATE_TESTS.dbo.providers')

    with raises(Exception):
        assert change_detection.has_table('bad table name')

def test_returns_data(test_gdb):
    hashes = _get_hashes([str(Path(test_gdb) / 'ChangeDetection')])
    expected = {'update_tests.dbo.counties': '1',
                'update_tests.dbo.providers': '2',
                'counties': '5'}

    assert hashes == expected

def test_throw_on_duplicate_table_name(test_gdb):
    tables = ['ChangeDetection', 'ChangeDetectionWithDup']

    with raises(Exception):
        assert _get_hashes([str(Path(test_gdb) / table) for table in tables])

def test_throw_on_bad_path(test_gdb):
    tables = ['ChangeDetection', 'BadPath']

    with raises(Exception):
        assert _get_hashes([str(Path(test_gdb) / table) for table in tables])

core.init(logging.getLogger('forklift'))
def test_updates_data(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    scratch_hash_table = str(Path(arcpy.env.scratchGDB) / Path(hash_table).name)
    scratch_destination = str(Path(arcpy.env.scratchGDB) / 'Counties')
    temp_data = [scratch_hash_table, scratch_destination]
    for dataset in temp_data:
        if arcpy.Exists(dataset):
            arcpy.management.Delete(dataset)
    arcpy.management.Copy(hash_table, scratch_hash_table)

    change_detection = ChangeDetection(['ChangeDetection'], test_gdb, hash_table=scratch_hash_table)

    table = 'counties'
    crate = Crate(table, test_gdb, arcpy.env.scratchGDB, Path(scratch_destination).name)
    crate.result = (Crate.CREATED, None)
    core._create_destination_data(crate, skip_hash_field=True)
    change_detection.current_hashes[table] = '8'
    result = change_detection.update(crate)

    where = f'{table_name_field} = \'{table}\''
    with arcpy.da.SearchCursor(scratch_hash_table, [hash_field], where_clause=where) as cursor:
        assert next(cursor)[0] == '8'

    assert result[0] == Crate.CREATED

    change_detection.current_hashes[table] = '9'
    crate.result = (Crate.UNINITIALIZED, None)
    result = change_detection.update(crate)

    where = f'{table_name_field} = \'{table}\''
    with arcpy.da.SearchCursor(scratch_hash_table, [hash_field], where_clause=where) as cursor:
        assert next(cursor)[0] == '9'

    assert result[0] == Crate.UPDATED

def test_invalid_data(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    change_detection = ChangeDetection(['ChangeDetection'], test_gdb, hash_table=hash_table)

    table = 'update_tests.dbo.providers'
    crate = Crate(table, 'someWorkspace', arcpy.env.scratchGDB, Path(test_gdb).name)
    result = change_detection.update(crate)

    assert result[0] == Crate.INVALID_DATA

def test_preserves_globalids(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    scratch_hash_table = str(Path(arcpy.env.scratchGDB) / Path(hash_table).name)
    scratch_destination = str(Path(arcpy.env.scratchGDB) / 'GlobalIds')
    temp_data = [scratch_hash_table, scratch_destination]
    for dataset in temp_data:
        if arcpy.Exists(dataset):
            arcpy.management.Delete(dataset)
    arcpy.management.Copy(hash_table, scratch_hash_table)
    test_sde = str(Path(test_data_folder) / 'UPDATE_TESTS.sde')

    change_detection = ChangeDetection(['ChangeDetection'], test_sde, hash_table=scratch_hash_table)

    table = 'GlobalIds'
    crate = Crate(table, test_sde, str(Path(scratch_destination).parent), Path(scratch_destination).name)
    crate.result = (Crate.CREATED, None)
    core._create_destination_data(crate, skip_hash_field=True)
    change_detection.current_hashes[f'update_tests.dbo.{table.casefold()}'] = 'hash'
    result = change_detection.update(crate)

    assert result[0] == Crate.CREATED

    with arcpy.da.SearchCursor(scratch_destination, ['GlobalID', 'NAME'], 'NAME = \'JUAB\'') as cursor:
        assert next(cursor)[0] == '{29B2946D-695C-4387-BAB7-4773B8DC0E6D}'

def test_preserves_globalids_table(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    scratch_hash_table = str(Path(arcpy.env.scratchGDB) / Path(hash_table).name)
    scratch_destination = str(Path(arcpy.env.scratchGDB) / 'GlobalIds')
    temp_data = [scratch_hash_table, scratch_destination]
    for dataset in temp_data:
        if arcpy.Exists(dataset):
            arcpy.management.Delete(dataset)
    arcpy.management.Copy(hash_table, scratch_hash_table)
    test_sde = str(Path(test_data_folder) / 'UPDATE_TESTS.sde')

    change_detection = ChangeDetection(['ChangeDetection'], test_sde, hash_table=scratch_hash_table)

    table = 'GlobalIdsTable'
    crate = Crate(table, test_sde, str(Path(scratch_destination).parent), Path(scratch_destination).name)
    crate.result = (Crate.CREATED, None)
    core._create_destination_data(crate, skip_hash_field=True)
    change_detection.current_hashes[f'update_tests.dbo.{table.casefold()}'] = 'hash'
    result = change_detection.update(crate)

    assert result[0] == Crate.CREATED

    with arcpy.da.SearchCursor(scratch_destination, ['GlobalID', 'NAME'], 'NAME = \'JUAB\'') as cursor:
        assert next(cursor)[0] == '{D5868F73-B65A-4B11-B346-D00E7A5043F7}'

def test_can_handle_globalid_fields_without_index(test_gdb):
    hash_table = str(Path(test_gdb) / 'TableHashes')
    scratch_hash_table = str(Path(arcpy.env.scratchGDB) / Path(hash_table).name)
    scratch_destination = str(Path(arcpy.env.scratchGDB) / 'GlobalIds')
    temp_data = [scratch_hash_table, scratch_destination]
    for dataset in temp_data:
        if arcpy.Exists(dataset):
            arcpy.management.Delete(dataset)
    arcpy.management.Copy(hash_table, scratch_hash_table)
    test_sde = str(Path(test_data_folder) / 'UPDATE_TESTS.sde')

    change_detection = ChangeDetection(['ChangeDetection'], test_sde, hash_table=scratch_hash_table)

    table = 'GlobalIdsNoIndex'
    crate = Crate(table, test_sde, arcpy.env.scratchGDB, Path(scratch_destination).name)
    crate.result = (Crate.CREATED, None)
    core._create_destination_data(crate, skip_hash_field=True)
    change_detection.current_hashes[f'update_tests.dbo.{table.casefold()}'] = 'hash'
    result = change_detection.update(crate)

    assert result[0] == Crate.CREATED
