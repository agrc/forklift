#!/usr/bin/env python
# * coding: utf8 *
'''
change_detection.py
a module to track changes from change detection tables
'''
import logging
from os import path

import arcpy

from . import config
from .core import update_while_preserving_global_ids
from .models import Crate

log = logging.getLogger('forklift')
hash_fgdb_name = 'changedetection.gdb'
hash_fgdb = path.join(config.get_config_prop('hashLocation'), hash_fgdb_name)
hash_table_name = 'TableHashes'
hash_table = path.join(hash_fgdb, hash_table_name)
table_name_field = 'table_name'
hash_field = 'hash'


class ChangeDetection(object):
    '''A class that models data obtained from the change detection tables
    '''

    def __init__(self, table_paths, root_folder, hash_table=hash_table):
        self.hash_table = hash_table
        if not arcpy.Exists(hash_table):
            log.info(f'creating change detection table: {hash_table}')
            arcpy.management.CreateTable(path.dirname(hash_table), path.basename(hash_table))
            arcpy.management.AddField(hash_table, table_name_field, 'TEXT')
            arcpy.management.AddField(hash_table, hash_field, 'TEXT')

        self.current_hashes = _get_hashes([path.join(root_folder, table_path) for table_path in table_paths])
        self.previous_hashes = _get_hashes([hash_table])

    def has_table(self, table_name):
        '''table_name: string
        returns a boolean indicating if there is a current hash for the given table
        '''
        return table_name.lower() in self.current_hashes

    def has_changed(self, table_name):
        '''table_name: string
        returns a boolean indicating if a tables hash has changed
        '''
        table_name = table_name.lower()

        if table_name not in self.current_hashes:
            raise Exception(f'{table_name} not found in current hashes!')

        if table_name not in self.previous_hashes:
            return True

        return self.current_hashes[table_name] != self.previous_hashes[table_name]

    def update(self, crate):
        '''crate: Crate
        updates the hash table with the current hash and truncates and loads the destination data

        returns an updates crate status
        '''
        status = Crate.UPDATED
        if crate.result[0] == Crate.INVALID_DATA:
            return crate.result
        elif crate.result[0] == Crate.CREATED:
            status = Crate.CREATED

        if ('hasGlobalID' in crate.source_describe and crate.source_describe['hasGlobalID']):
            update_while_preserving_global_ids(crate, skip_hash_field=True)
        else:
            log.info(f'truncating and loading {crate.destination}')
            arcpy.management.TruncateTable(crate.destination)

            with arcpy.EnvManager(geographicTransformations=crate.geographic_transformation):
                arcpy.management.Append(crate.source, crate.destination, schema_type='NO_TEST')

        table_name = crate.source_name.lower()
        with arcpy.da.UpdateCursor(self.hash_table, [hash_field], where_clause=f'{table_name_field} = \'{table_name}\'') as cursor:
            try:
                next(cursor)
                log.info(f'updating value in hash table for {table_name}')
                cursor.updateRow((self.current_hashes[table_name],))
            except StopIteration:
                log.info(f'adding new row in hash table for {table_name}')
                with arcpy.da.InsertCursor(self.hash_table, [table_name_field, hash_field]) as insert_cursor:
                    insert_cursor.insertRow((table_name, self.current_hashes[table_name]))

        return (status, None)


def _get_hashes(table_paths):
    '''table_paths: string[] - paths to change detection tables relative to the garage
    root: string - path to root directory where table_paths is relative to

    returns a dictionary of table names to hashes
    '''
    data = {}

    for table_path in table_paths:
        log.info(f'getting change detection data from: {table_path}')
        with arcpy.da.SearchCursor(table_path, ['table_name', 'hash']) as cursor:
            for table_name, hash_value in cursor:
                if table_name in data:
                    raise Exception(f'duplicate table name found in change detection tables: {table_name}')
                data[table_name] = hash_value

    return data
