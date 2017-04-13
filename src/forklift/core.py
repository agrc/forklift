#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating the data associated with a models.Crate
'''

import arcpy
from config import config_location
from exceptions import ValidationException
from models import Changes, Crate
from os import path
from hashlib import md5

log = None

reproject_temp_suffix = '_fl'

hash_att_field = 'att_hash'

hash_geom_field = 'geom_hash'

hash_id_field = 'Id'

src_id_field = 'src_id' + reproject_temp_suffix

garage = path.dirname(config_location)

_hash_gdb = 'hashes.gdb'
_scratch_gdb = 'scratch.gdb'

scratch_gdb_path = path.join(garage, _scratch_gdb)
hash_gdb_path = path.join(garage, _hash_gdb)


def init(logger):
    '''
    make sure forklift is ready to run. create the hashing gdb and clear out the scratch geodatabase
    logger is passed in from cli.py (rather than just setting it via `log = logging.getLogger('forklift')`)
    to enable other projects to use this module without colliding with the same logger'''
    global log
    log = logger

    #: create gdb if needed
    if not arcpy.Exists(hash_gdb_path):
        log.info('%s does not exist. creating', hash_gdb_path)
        arcpy.CreateFileGDB_management(garage, _hash_gdb)

    if arcpy.Exists(scratch_gdb_path):
        log.info('%s exist. recreating', scratch_gdb_path)
        arcpy.Delete_management(scratch_gdb_path)

    arcpy.CreateFileGDB_management(garage, _scratch_gdb)

    arcpy.ClearEnvironment('workspace')


def optimize_internal_gdbs():
    if arcpy.Exists(hash_gdb_path):
        log.info('%s compacting', hash_gdb_path)
        arcpy.Compact_management(hash_gdb_path)

    if arcpy.Exists(scratch_gdb_path):
        log.info('%s deleting', scratch_gdb_path)
        arcpy.Delete_management(scratch_gdb_path)


def update(crate, validate_crate):
    '''
    crate: models.Crate
    validate_crate: models.Pallet.validate_crate

    returns: String
        One of the result string constants from models.Crate

    Checks to see if a crate can be updated by using validate_crate (if implemented
    within the pallet) or check_schema otherwise. If the crate is valid it
    then updates the data.'''
    arcpy.env.geographicTransformations = crate.geographic_transformation
    change_status = (Crate.NO_CHANGES, None)

    def truncate_where_clause(txt):
        max = 100
        if txt is not None and len(txt) > max:
            return txt[:max - 1] + '...'
        else:
            return txt

    try:
        if not arcpy.Exists(crate.destination):
            log.debug('%s does not exist. creating', crate.destination)
            _create_destination_data(crate)

            #: remove hash table entry for destination that doers not exist
            if arcpy.Exists(path.join(hash_gdb_path, crate.name)):
                arcpy.Delete_management(path.join(hash_gdb_path, crate.name))

            change_status = (Crate.CREATED, None)

        #: check for custom validation logic, otherwise do a default schema check
        try:
            has_custom = validate_crate(crate)
            if has_custom == NotImplemented:
                check_schema(crate)
        except ValidationException as e:
            log.warn('validation error: %s for crate %r', e.message, crate, exc_info=True)
            return (Crate.INVALID_DATA, e.message)

        #: create source hash and store
        changes = _hash(crate, hash_gdb_path)

        if not changes.has_changes():
            log.debug('No changes found.')

        #: delete unaccessed hashes
        if changes.has_deletes():
            log.debug('Number of rows to be deleted: %d', len(changes._deletes))
            status, message = change_status
            if status != Crate.CREATED:
                change_status = (Crate.UPDATED, None)

            edit_session = arcpy.da.Editor(crate.destination_workspace)
            edit_session.startEditing(False, False)
            edit_session.startOperation()

            destination_key = arcpy.Describe(crate.destination).OIDFieldName

            log.debug('deleting from destintation table')
            with arcpy.da.UpdateCursor(crate.destination, destination_key) as cursor:
                for row in cursor:
                    if row[0] in changes._deletes:
                        cursor.deleteRow()

            log.debug('deleting from hash table')
            with arcpy.da.UpdateCursor(path.join(hash_gdb_path, crate.name), hash_id_field) as cursor:
                for row in cursor:
                    if row[0] in changes._deletes:
                        cursor.deleteRow()

            edit_session.stopOperation()
            edit_session.stopEditing(True)

        #: add new/updated rows
        if changes.has_adds():
            log.debug('Number of rows to be added: %d', len(changes.adds))
            status, message = change_status
            if status != Crate.CREATED:
                change_status = (Crate.UPDATED, None)

            hash_table = path.join(hash_gdb_path, crate.name)

            #: reproject data if source is different than destination
            if crate.needs_reproject():
                changes.table = arcpy.Project_management(changes.table, changes.table + reproject_temp_suffix, crate.destination_coordinate_system,
                                                         crate.geographic_transformation)[0]

            log.debug('starting edit session...')
            edit_session = arcpy.da.Editor(crate.destination_workspace)
            edit_session.startEditing(False, False)
            edit_session.startOperation()
            log.debug('edit session and operation started')

            #: strip off duplicated primary key added during hashing since it's no longer necessary
            log.debug('adds features')

            if not crate.is_table():
                shape_field_index = -2
                changes.fields[shape_field_index] = changes.fields[shape_field_index].rstrip('WKT')

            fields = changes.fields[:-1]

            #: cache this so we don't have to call it for every record
            is_table = crate.is_table()
            hash_fields = [hash_id_field, hash_att_field, hash_geom_field]
            with arcpy.da.SearchCursor(changes.table, changes.fields) as add_cursor,\
                    arcpy.da.InsertCursor(crate.destination, fields) as cursor, \
                    arcpy.da.InsertCursor(hash_table, hash_fields) as hash_cursor:
                for row in add_cursor:
                    primary_key = row[-1]

                    #: skip null geometries
                    if not is_table and row[shape_field_index] is None:
                        continue

                    #: update/store hash lookup using oid from insert into destination
                    hash_cursor.insertRow((cursor.insertRow(row[:-1]),) + changes.adds[primary_key])

            log.debug('stopping edit session (saving edits)')
            edit_session.stopOperation()
            edit_session.stopEditing(True)

        #: sanity check the row counts between source and destination
        count_status, count_message = _check_counts(crate, changes)
        if not count_status:
            return (Crate.WARNING, count_message)

        return change_status
    except Exception as e:
        log.error('unhandled exception: %s for crate %r', e.message, crate, exc_info=True)
        try:
            log.warn('stopping edit session (not saving edits)')
            edit_session.abortOperation()
            edit_session.stopEditing(False)
        except:
            pass

        return (Crate.UNHANDLED_EXCEPTION, e.message)
    finally:
        arcpy.ResetEnvironments()
        arcpy.ClearWorkspaceCache_management()


def _hash(crate, hash_path):
    '''
    crate: Crate

    hash_path: string path to hash gdb

    returns a Changes model with deltas for the source'''
    #: TODO cache lookup table for repeat offenders
    #: create hash lookup table for source data
    if not arcpy.Exists(path.join(hash_path, crate.name)):
        log.debug('%s does not exist. creating', crate.name)
        table = arcpy.CreateTable_management(hash_path, crate.name)
        arcpy.AddField_management(table, hash_id_field, 'LONG')
        arcpy.AddField_management(table, hash_att_field, 'TEXT', field_length=32)
        arcpy.AddField_management(table, hash_geom_field, 'TEXT', field_length=32)

        #: truncate destination table since we are hashing for the first time
        arcpy.TruncateTable_management(crate.destination)

    shape_token = 'SHAPE@WKT'

    log.info('checking for changes...')
    #: finding and filtering common fields between source and destination
    fields = set([fld.name for fld in arcpy.ListFields(crate.destination)]) & set([fld.name for fld in arcpy.ListFields(crate.source)])
    fields = _filter_fields(fields, crate.source_primary_key)

    #: keep track of OID token in order to remove from hashing
    primary_key_index = -1
    sql_clause = (None, 'ORDER BY {}'.format(crate.source_primary_key))

    if not crate.is_table():
        fields.append(shape_token)
        primary_key_index = -2

    changes = Changes(list(fields))
    changes.table = crate.source
    #: duplicate primary key so we can relate the hashes in the change model adds back to the source
    changes.fields.append(crate.source_primary_key)

    attribute_hashes, geometry_hashes = _get_hash_lookups(crate.name, hash_gdb_path)
    total_rows = 0
    unique_salty_id = 0

    insert_cursor = None
    temp_table = path.join(scratch_gdb_path, crate.name)
    if arcpy.Exists(temp_table):
        arcpy.Delete_management(temp_table)

    if not crate.is_table():
        changes.table = arcpy.CreateFeatureclass_management(scratch_gdb_path,
                                                            crate.name,
                                                            geometry_type=crate.source_describe.shapeType.upper(),
                                                            template=crate.source,
                                                            spatial_reference=crate.source_describe.spatialReference)[0]
    else:
        changes.table = arcpy.CreateTable_management(scratch_gdb_path,
                                                     crate.name,
                                                     template=crate.source)[0]

    arcpy.AddField_management(changes.table, src_id_field, 'TEXT')
    if crate.source_describe.dataType == 'ShapeFile':
        log.info('adding FID field for shapefile comparison')
        arcpy.AddField_management(changes.table, 'FID', 'LONG')
    #: reset duplicated key because wtf
    changes.fields[-1] = src_id_field
    insert_cursor = arcpy.da.InsertCursor(changes.table, changes.fields)

    with arcpy.da.SearchCursor(crate.source, fields, sql_clause=sql_clause) as cursor:
        def parse_id_as_int(id):
            return str(int(id))

        def parse_id_as_string(id):
            return str(id)

        if crate.source_primary_key_type == int:
            #: We are parsing as int because this could be any type of number
            #: including a float which causes issues by adding a ".0".
            #: Forklift assumes that all source_primary_key values can be parsed
            #: as whole numbers.
            id_parser = parse_id_as_int
        else:
            id_parser = parse_id_as_string

        for row in cursor:
            total_rows += 1
            unique_salty_id += 1
            #: create shape hash
            geom_hash_digest = None
            src_id = id_parser(row[primary_key_index])
            if not crate.is_table():
                shape_wkt = row[-1]

                #: skip features with empty geometry
                if shape_wkt is None:
                    log.warn('Empty geometry found in %s: %s', crate.source_primary_key, src_id)
                    total_rows -= 1
                    continue

                geom_hash_digest = _create_hash(shape_wkt, unique_salty_id)

            #: create attribute hash
            attribute_hash_digest = _create_hash(str(row[:primary_key_index]), unique_salty_id)

            #: check for new feature
            if attribute_hash_digest not in attribute_hashes or (geom_hash_digest is not None and geom_hash_digest not in geometry_hashes):
                #: update or add
                #: insert into temp table
                insert_cursor.insertRow(row + (src_id,))
                #: add to adds
                changes.adds[src_id] = (attribute_hash_digest, geom_hash_digest)
            else:
                #: remove not modified hash from hashes
                attribute_hashes.pop(attribute_hash_digest)
                if geom_hash_digest is not None:
                    geometry_hashes.pop(geom_hash_digest)

                changes.unchanged[src_id] = (attribute_hash_digest, geom_hash_digest)

    changes.determine_deletes(attribute_hashes, geometry_hashes)
    changes.total_rows = total_rows
    del insert_cursor

    return changes


def _create_destination_data(crate):
    if not path.exists(crate.destination_workspace):
        if crate.destination_workspace.endswith('.gdb'):
            log.warning('destination not found; creating %s', crate.destination_workspace)
            arcpy.CreateFileGDB_management(path.dirname(crate.destination_workspace), path.basename(crate.destination_workspace))
        else:
            raise Exception('destination_workspace does not exist! {}'.format(crate.destination_workspace))

    if crate.is_table():
        log.warn('creating new table: %s', crate.destination)
        arcpy.CreateTable_management(crate.destination_workspace, crate.destination_name, crate.source)

        return

    log.warn('creating new feature class: %s', crate.destination)

    arcpy.CreateFeatureclass_management(crate.destination_workspace,
                                        crate.destination_name,
                                        crate.source_describe.shapeType.upper(),
                                        crate.source,
                                        spatial_reference=crate.destination_coordinate_system or crate.source_describe.spatialReference)

    if crate.source_describe.dataType == 'ShapeFile':
        log.info('adding FID field for shapefile comparison')
        arcpy.AddField_management(crate.destination, 'FID', 'LONG')


def _create_hash(string, salt):
    hasher = md5(string)
    hasher.update(str(salt))

    return hasher.hexdigest()


def _get_hash_lookups(name, hash_path):
    '''
    name: string name of the crate table in the hash geodatabase

    hash_path: string path to hash gdb

    returns a tuple with the hash lookups for attributes and geometries'''
    hash_lookup = {}
    geo_hash_lookup = {}
    fields = [hash_id_field, hash_att_field, hash_geom_field]

    with arcpy.da.SearchCursor(path.join(hash_path, name), fields) as cursor:
        for id, att_hash, geo_hash in cursor:
            if att_hash is not None:
                hash_lookup[str(att_hash)] = id
            if geo_hash is not None:
                geo_hash_lookup[str(geo_hash)] = id

    return (hash_lookup, geo_hash_lookup)


def check_schema(crate):
    '''
    crate: Crate

    returns: Boolean - True if the schemas match, raises ValidationException if no match'''

    def get_fields(dataset):
        field_dict = {}

        for field in arcpy.ListFields(dataset):
            #: don't worry about comparing managed fields
            if not _is_naughty_field(field.name) and field.name not in ['OBJECTID', 'FID']:
                field_dict[field.name.upper()] = field

        return field_dict

    def abstract_type(type):
        if type in ['Double', 'Integer', 'Single', 'SmallInteger']:
            return 'Numeric'
        else:
            return type

    log.info('checking schema...')
    missing_fields = []
    mismatching_fields = []
    source_fields = get_fields(crate.source)
    destination_fields = get_fields(crate.destination)

    for field_key in destination_fields.keys():
        # make sure that all fields from destination are in source
        # not sure that we care if there are fields in source that are not in destination
        destination_fld = destination_fields[field_key]
        if field_key not in source_fields.keys():
            missing_fields.append(destination_fld.name)
        else:
            source_fld = source_fields[field_key]
            if abstract_type(source_fld.type) != abstract_type(destination_fld.type):
                mismatching_fields.append('{}: source type of {} does not match destination type of {}'
                                          .format(source_fld.name, source_fld.type, destination_fld.type))
            elif source_fld.type == 'String':

                def truncate_field_length(field):
                    if field.length > 4000:
                        log.warn('%s is longer than 4000 characters. Truncation may occur.', field.name)
                        return 4000
                    else:
                        return field.length

                source_fld.length = truncate_field_length(source_fld)
                destination_fld.length = truncate_field_length(destination_fld)
                if source_fld.length != destination_fld.length:
                    mismatching_fields.append('{}: source length of {} does not match destination length of {}'
                                              .format(source_fld.name, source_fld.length, destination_fld.length))

    if len(missing_fields) > 0:
        msg = 'Missing fields in {}: {}'.format(crate.source, ', '.join(missing_fields))
        log.warn(msg)

        raise ValidationException(msg)
    elif len(mismatching_fields) > 0:
        msg = 'Mismatching fields in {}: {}'.format(crate.source, ', '.join(mismatching_fields))
        log.warn(msg)

        raise ValidationException(msg)
    else:
        return True


def _filter_fields(fields, source_primary_key):
    '''
    fields: String[]
    source_primary_key: string

    returns: String[]

    Filters out fields that mess up the update logic
    and move the primary be the last field so that we can filter it out of the hash.'''
    new_fields = [field for field in fields if not _is_naughty_field(field)]
    new_fields.sort()

    try:
        new_fields.remove(source_primary_key)
    except ValueError:
        #: key not common to both source and destination. add it anyway
        pass

    new_fields.append(source_primary_key)

    return new_fields


def _is_naughty_field(fld):
    #: global id's do not export to file geodatabase
    #: removes shape, shape_length etc
    #: removes objectid_ which is created by geoprocessing tasks and wouldn't be in destination source
    #: TODO: Deal with possibility of OBJECTID_* being the OIDFieldName
    return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID'] or fld.startswith('OBJECTID_')


def _check_counts(crate, changes):
    '''
    crate: Crate
    changes: Changes

    Validates that the row counts between source and destination are the same (ignoring empty geometries)

    returns: (valid, message)
        valid: Boolean - true if counts match
        message: String - warning message if any
    '''

    destination_rows = len([row for row in arcpy.da.SearchCursor(crate.destination, ['*'])])
    source_rows = changes.total_rows
    valid = source_rows == destination_rows

    if not valid:
        message = 'Source row count ({}) does not match destination count ({})!'.format(source_rows, destination_rows)
    else:
        message = ''

    return (valid, message)
