#!/usr/bin/env python
# * coding: utf8 *
'''
test_change_detection.py
a module containing tests for the change detection module
'''
import logging
import unittest
from os import path
from pathlib import Path

from pytest import raises

import arcpy
from forklift import core
from forklift.change_detection import (ChangeDetection, _get_hashes,
                                       hash_field, table_name_field)
from forklift.models import Crate

current_folder = path.dirname(path.abspath(__file__))
test_data_folder = path.join(current_folder, 'data')
test_fgdb = path.join(test_data_folder, 'test_change_detection', 'data.gdb')
hash_table = path.join(test_fgdb, 'TableHashes')


class TestChangeDetection(unittest.TestCase):
    def test_has_table(self):
        change_detection = ChangeDetection(['ChangeDetection'], test_fgdb, hash_table=hash_table)

        self.assertTrue(change_detection.has_table('UPDATE_TESTS.dbo.counties'))
        self.assertFalse(change_detection.has_table('bad table name'))

    def test_has_changed(self):
        change_detection = ChangeDetection(['ChangeDetection'], test_fgdb, hash_table=hash_table)

        self.assertFalse(change_detection.has_changed('UPDATE_TESTS.dbo.counties'))
        self.assertTrue(change_detection.has_changed('UPDATE_TESTS.dbo.providers'))

        with raises(Exception):
            assert change_detection.has_table('bad table name')


class TestGetHashes(unittest.TestCase):
    def test_returns_data(self):
        hashes = _get_hashes([path.join(test_fgdb, 'ChangeDetection')])
        expected = {'update_tests.dbo.counties': '1',
                    'update_tests.dbo.providers': '2',
                    'counties': '5'}

        self.assertEqual(hashes, expected)

    def test_throw_on_duplicate_table_name(self):
        tables = ['ChangeDetection', 'ChangeDetectionWithDup']

        with raises(Exception):
            assert _get_hashes([path.join(test_fgdb, table) for table in tables])

    def test_throw_on_bad_path(self):
        tables = ['ChangeDetection', 'BadPath']

        with raises(Exception):
            assert _get_hashes([path.join(test_fgdb, table) for table in tables])


core.init(logging.getLogger('forklift'))
class TestUpdate(unittest.TestCase):
    def test_updates_data(self):
        scratch_hash_table = path.join(arcpy.env.scratchGDB, path.basename(hash_table))
        scratch_destination = path.join(arcpy.env.scratchGDB, 'Counties')
        temp_data = [scratch_hash_table, scratch_destination]
        for dataset in temp_data:
            if arcpy.Exists(dataset):
                arcpy.management.Delete(dataset)
        arcpy.management.Copy(hash_table, scratch_hash_table)

        change_detection = ChangeDetection(['ChangeDetection'], test_fgdb, hash_table=scratch_hash_table)

        table = 'counties'
        crate = Crate(table, test_fgdb, arcpy.env.scratchGDB, path.basename(scratch_destination))
        crate.result = (Crate.CREATED, None)
        core._create_destination_data(crate, skip_hash_field=True)
        change_detection.current_hashes[table] = '8'
        result = change_detection.update(crate)

        where = f'{table_name_field} = \'{table}\''
        with arcpy.da.SearchCursor(scratch_hash_table, [hash_field], where_clause=where) as cursor:
            self.assertEqual(next(cursor)[0], '8')

        self.assertEqual(result[0], Crate.CREATED)

        change_detection.current_hashes[table] = '9'
        crate.result = (Crate.UNINITIALIZED, None)
        result = change_detection.update(crate)

        where = f'{table_name_field} = \'{table}\''
        with arcpy.da.SearchCursor(scratch_hash_table, [hash_field], where_clause=where) as cursor:
            self.assertEqual(next(cursor)[0], '9')

        self.assertEqual(result[0], Crate.UPDATED)

    def test_invalid_data(self):
        scratch_hash_table = path.join(arcpy.env.scratchGDB, path.basename(hash_table))
        scratch_destination = path.join(arcpy.env.scratchGDB, 'Counties')
        temp_data = [scratch_hash_table, scratch_destination]
        for dataset in temp_data:
            if arcpy.Exists(dataset):
                arcpy.management.Delete(dataset)
        arcpy.management.Copy(hash_table, scratch_hash_table)

        change_detection = ChangeDetection(['ChangeDetection'], test_fgdb, hash_table=scratch_hash_table)

        table = 'update_tests.dbo.providers'
        crate = Crate(table, 'someWorkspace', arcpy.env.scratchGDB, path.basename(scratch_destination))
        result = change_detection.update(crate)

        self.assertEqual(result[0], Crate.INVALID_DATA)

    def test_preserves_globalids(self):
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

        self.assertEqual(result[0], Crate.CREATED)

        with arcpy.da.SearchCursor(scratch_destination, ['GlobalID', 'NAME'], 'NAME = \'JUAB\'') as cursor:
            self.assertEqual(next(cursor)[0], '{29B2946D-695C-4387-BAB7-4773B8DC0E6D}')

    def test_can_handle_globalid_fields_without_index(self):
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

        self.assertEqual(result[0], Crate.CREATED)
