#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating the data associated with a models.Crate
'''

import arcpy
import logging
from config import config_location
from exceptions import ValidationException
from models import Changes, Crate
from os import path
from hashlib import md5

log = logging.getLogger('forklift')

reproject_temp_suffix = '_fl'

hash_att_field = 'att_hash'

hash_geom_field = 'geom_hash'

hash_id_field = 'Id'

garage = path.dirname(config_location)

_hash_gdb = 'hashes.gdb'

hash_gdb_path = path.join(garage, _hash_gdb)


def init():
    #: create gdb if needed
    if not arcpy.Exists(hash_gdb_path):
        log.info('%s does not exist. creating', hash_gdb_path)
        arcpy.CreateFileGDB_management(garage, _hash_gdb)

    #: clear out scratchGDB
    arcpy.env.workspace = arcpy.env.scratchGDB
    log.info('clearing out scratchGDB')
    for featureClass in arcpy.ListFeatureClasses():
        log.debug('deleting: %s', featureClass)
        arcpy.Delete_management(featureClass)

    arcpy.ClearEnvironment('workspace')


def update(crate, validate_crate):
    '''
    crate: models.Crate
    validate_crate: models.Pallet.validate_crate

    returns: String
        One of the result string constants from models.Crate

    Checks to see if a crate can be updated by using validate_crate (if implemented
    within the pallet) or check_schema otherwise. If the crate is valid it
    then updates the data.
    '''

    arcpy.env.geographicTransformations = crate.geographic_transformation

    def remove_temp_table(table):
        if table is not None and table.endswith(reproject_temp_suffix) and arcpy.Exists(table):
            log.debug('deleting %s', table)
            arcpy.Delete_management(table)

    change_status = (Crate.NO_CHANGES, None)

    try:
        if not arcpy.Exists(crate.source):
            status, message = _try_to_find_data_source_by_name(crate)
            if not status:
                return (Crate.INVALID_DATA, message)

        if not arcpy.Exists(crate.destination):
            log.debug('%s does not exist. creating', crate.destination)
            _create_destination_data(crate)
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

        source_describe = arcpy.Describe(crate.source)
        is_table = _is_table(crate)
        needs_reproject = not is_table and (source_describe.spatialReference.name != arcpy.Describe(crate.destination).spatialReference.name)
        #: create source hash and store
        changes = _hash(crate, hash_gdb_path, needs_reproject)

        if not changes.has_changes():
            log.debug('No changes found.')

        #: delete unaccessed hashes
        if changes.has_deletes():
            log.debug('Number of rows deleted: %d', len(changes._deletes))
            status, message = change_status
            if status != Crate.CREATED:
                change_status = (Crate.UPDATED, None)

            edit_session = arcpy.da.Editor(crate.destination_workspace)
            edit_session.startEditing(False, False)
            edit_session.startOperation()

            with arcpy.da.UpdateCursor(crate.destination, ['OID@'], changes.get_delete_where_clause()) as cursor:
                for row in cursor:
                    cursor.deleteRow()

            edit_session.stopOperation()
            edit_session.stopEditing(True)

            with arcpy.da.UpdateCursor(path.join(hash_gdb_path, crate.name), [hash_id_field], changes.get_delete_where_clause()) as cursor:
                for row in cursor:
                    cursor.deleteRow()

        #: add new/updated rows
        if changes.has_adds():
            log.debug('Number of rows added: %d', len(changes.adds))
            status, message = change_status
            if status != Crate.CREATED:
                change_status = (Crate.UPDATED, None)

            hash_table = path.join(hash_gdb_path, crate.name)

            #: reproject data if source is different than destination
            source_describe = arcpy.Describe(crate.source)
            if needs_reproject:
                changes.table = arcpy.Project_management(changes.table, changes.table + '_projected', crate.destination_coordinate_system,
                                                         crate.geographic_transformation)[0]

            log.debug('starting edit session...')
            edit_session = arcpy.da.Editor(crate.destination_workspace)
            edit_session.startEditing(False, False)
            edit_session.startOperation()
            with arcpy.da.SearchCursor(changes.table, changes.fields) as addCursor,\
                    arcpy.da.InsertCursor(crate.destination, changes.fields[:-1]) as cursor, \
                    arcpy.da.InsertCursor(hash_table, [hash_id_field, hash_att_field, hash_geom_field]) as hash_cursor:
                for row in addCursor:
                    primary_key = row[-1]
                    dest_id = cursor.insertRow(row[:-1])
                    #: update/store hash lookup
                    hash_cursor.insertRow((dest_id,) + changes.adds[primary_key])

            log.debug('stopping edit session (saving edits)')
            edit_session.stopOperation()
            edit_session.stopEditing(True)

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


def _hash(crate, hash_path, needs_reproject):
    '''
    crate: Crate

    hash_path: string path to hash gdb

    needs_reproject: bool true if the dataset needs to be reprojected

    returns a Changes model with deltas for the source
    '''
    #: TODO cache lookup table for repeat offenders
    #: create hash lookup table for source data
    if not arcpy.Exists(path.join(hash_path, crate.name)):
        log.debug('%s does not exist. creating', crate.name)
        table = arcpy.CreateTable_management(hash_path, crate.name)
        arcpy.AddField_management(table, hash_id_field, 'LONG', field_length=32)
        arcpy.AddField_management(table, hash_att_field, 'TEXT', field_length=32)
        arcpy.AddField_management(table, hash_geom_field, 'TEXT', field_length=32)

        #: truncate destination table since we are hashing for the first time
        arcpy.TruncateTable_management(crate.destination)

    shape_token = 'SHAPE@'
    is_table = _is_table(crate)
    src_id_field = 'src_id'

    log.info('checking for changes...')
    #: finding and filtering common fields between source and destination
    fields = set([fld.name for fld in arcpy.ListFields(crate.destination)]) & set([fld.name for fld in arcpy.ListFields(crate.source)])
    fields = _filter_fields(fields)

    sql_clause = None

    #: keep track of OID token in order to remove from hashing
    att_hash_sub_index = None
    if 'OID@' in fields:
        att_hash_sub_index = -1
        source_describe = arcpy.Describe(crate.source)
        sql_clause = (None, 'ORDER BY {}'.format(source_describe.OIDFieldName))

    if not is_table:
        fields.append(shape_token)
        att_hash_sub_index = -2

    changes = Changes(list(fields))
    changes.table = crate.source
    changes.fields.append('OID@')
    #: TODO update to use with pickle or geodatabase
    attribute_hashes, geometry_hashes = _get_hash_lookups(crate.name, hash_gdb_path)
    unique_salt = 0

    insert_cursor = None
    if needs_reproject:
        changes.table = temp_table = arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB,
                                                                         crate.name,
                                                                         geometry_type=source_describe.shapeType.upper(),
                                                                         template=crate.source,
                                                                         spatial_reference=source_describe.spatialReference)[0]
        arcpy.AddField_management(temp_table, src_id_field, 'LONG')
        changes.fields[-1] = src_id_field
        insert_cursor = arcpy.da.InsertCursor(temp_table, changes.fields)

    with arcpy.da.SearchCursor(crate.source, fields, sql_clause=sql_clause) as cursor:
        for row in cursor:
            unique_salt += 1
            #: create shape hash
            geom_hash_digest = None
            if not is_table:
                shape = row[-1]

                #: skip features with empty geometry
                if shape is None:
                    continue
                geom_hash_digest = _create_hash(shape.WKT, unique_salt)

            #: create attribute hash
            attribute_hash_digest = _create_hash(str(row[:att_hash_sub_index]), unique_salt)

            #: check for new feature
            if attribute_hash_digest not in attribute_hashes or (geom_hash_digest is not None and geom_hash_digest not in geometry_hashes):
                #: update or add
                #: if reprojecting insert into temp table
                src_id = row[att_hash_sub_index]
                if needs_reproject:
                    insert_cursor.insertRow(row + (src_id,))
                #: add to adds
                changes.adds[src_id] = (attribute_hash_digest, geom_hash_digest)
            else:
                #: remove not modified hash from hashes
                attribute_hashes.pop(attribute_hash_digest)
                if geom_hash_digest is not None:
                    geometry_hashes.pop(geom_hash_digest)

    changes.determine_deletes(attribute_hashes, geometry_hashes)

    return changes


def _create_destination_data(crate):
    if not path.exists(crate.destination_workspace):
        if crate.destination_workspace.endswith('.gdb'):
            log.warning('destination not found; creating %s', crate.destination_workspace)
            arcpy.CreateFileGDB_management(path.dirname(crate.destination_workspace), path.basename(crate.destination_workspace))
        else:
            raise Exception('destination_workspace does not exist! {}'.format(crate.destination_workspace))

    if _is_table(crate):
        log.warn('creating new table: %s', crate.destination)
        arcpy.CreateTable_management(crate.destination_workspace, crate.destination_name, crate.source)

        return

    log.warn('creating new feature class: %s', crate.destination)

    source_describe = arcpy.Describe(crate.source)
    arcpy.CreateFeatureclass_management(crate.destination_workspace,
                                        crate.destination_name,
                                        source_describe.shapeType.upper(),
                                        crate.source,
                                        spatial_reference=crate.destination_coordinate_system or source_describe.spatialReference)


def _is_table(crate):
    '''
    crate: Crate

    returns True if the crate defines a table
    '''
    return arcpy.Describe(crate.source).datasetType == 'Table'


def _create_hash(string, salt):
    hasher = md5(string)
    hasher.update(str(salt))

    return hasher.hexdigest()


def _get_hash_lookups(name, hash_path):
    '''
    name: string name of the crate table in the hash geodatabase

    hash_path: string path to hash gdb

    returns a tuple with the hash lookups for attributes and geometries
    '''
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

    returns: Boolean - True if the schemas match, raises ValidationException if no match
    '''

    def get_fields(dataset):
        field_dict = {}

        for field in arcpy.ListFields(dataset):
            #: don't worry about comparing OBJECTID field
            if not _is_naughty_field(field.name) and field.name != 'OBJECTID':
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


def _filter_fields(fields):
    '''
    fields: String[]

    returns: String[]

    Filters out fields that mess up the update logic.
    '''

    new_fields = [field for field in fields if not _is_naughty_field(field)]
    new_fields.sort()

    # TODO: use arcpy.Describe().OIDFieldName
    if 'OBJECTID' in new_fields:
        new_fields.remove('OBJECTID')
        new_fields.append('OID@')

    return new_fields


def _is_naughty_field(fld):
    #: global id's do not export to file geodatabase
    #: removes shape, shape_length etc
    #: removes objectid_ which is created by geoprocessing tasks and wouldn't be in destination source
    return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID'] or fld.startswith('OBJECTID_')


def _try_to_find_data_source_by_name(crate):
    '''Given a crate, try to find the source name in the source workspace.
    if it is found, update the crate name so subsequent uses do not fail.

    returns a tuple (bool, message) describing the outcome'''
    if '.sde' not in crate.source.lower():
        return (None, 'Can\'t find data outside of sde')

    def filter_filenames(workspace, name):
        names = []
        walk = arcpy.da.Walk(workspace, followlinks=True)

        for dirpath, dirnames, filenames in walk:
            names = filenames

        #: could get a value like db.owner.***name and db.owner.name so filter on name
        return [fc for fc in names if fc.split('.')[2] == crate.source_name]

    names = filter_filenames(crate.source_workspace, crate.source_name)

    if names is None or len(names) < 1:
        return (False, 'No source data found for {}'.format(crate.source))

    if len(names) == 1:
        #: replace name with db.owner.name
        new_name = names[0]
        crate.set_source_name(new_name)
        log.warn('Source name changed to %s', new_name)

        return (True, new_name)

    if len(names) > 1:
        return (False, 'Duplcate names: {}'.format(','.join(names)))
