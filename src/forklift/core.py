#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating the data associated with a models.Crate
'''

import arcpy
import logging
from datetime import datetime
from exceptions import ValidationException
from itertools import izip
from math import fabs
from models import Crate
from os import path
from hashlib import md5

log = logging.getLogger('forklift')

reproject_temp_suffix = '__forklift'

attribute_hash_field = 'att_hash'

geometry_hash_field = 'geo_hash'


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

    def remove_temp_table(table):
        if table is not None and table.endswith(reproject_temp_suffix) and arcpy.Exists(table):
            log.debug('deleting %s', table)
            arcpy.Delete_management(table)

    arcpy.env.outputCoordinateSystem = crate.destination_coordinate_system
    arcpy.env.geographicTransformations = crate.geographic_transformation

    try:
        if not arcpy.Exists(crate.source):
            status, message = _try_to_find_data_source_by_name(crate)
            if not status:
                return (Crate.INVALID_DATA, message)

        if not arcpy.Exists(crate.destination):
            log.debug('%s does not exist. creating', crate.destination)
            _create_destination_data(crate)

            return (Crate.CREATED, None)

        #: check for custom validation logic, otherwise do a default schema check
        try:
            has_custom = validate_crate(crate)
            if has_custom == NotImplemented:
                check_schema(crate)
        except ValidationException as e:
            log.warn('validation error: %s for crate %r',
                     e.message,
                     crate,
                     exc_info=True)
            return (Crate.INVALID_DATA, e.message)
        # TODO separate change check from move_data, or remove has_changes and handle return value differently
        has_changes = True
        if has_changes:
            _move_data(crate)

            remove_temp_table(crate.destination + reproject_temp_suffix)

            return (Crate.UPDATED, None)
        else:
            remove_temp_table(crate.destination + reproject_temp_suffix)

            return (Crate.NO_CHANGES, None)
    except Exception as e:
        log.error('unhandled exception: %s for crate %r', e.message, crate, exc_info=True)
        return (Crate.UNHANDLED_EXCEPTION, e.message)
    finally:
        arcpy.env.outputCoordinateSystem = None
        arcpy.env.geographicTransformations = None


def _create_destination_data(crate):
    if not path.exists(crate.destination_workspace):
        if crate.destination_workspace.endswith('.gdb'):
            log.warning('destination not found; creating %s', crate.destination_workspace)
            arcpy.CreateFileGDB_management(path.dirname(crate.destination_workspace), path.basename(crate.destination_workspace))
        else:
            raise Exception('destination_workspace does not exist! {}'.format(crate.destination_workspace))
    if _is_table(crate):
        log.warn('creating new table: %s', crate.destination)
        arcpy.CopyRows_management(crate.source, crate.destination)
    else:
        log.warn('creating new feature class: %s', crate.destination)
        arcpy.env.outputCoordinateSystem = crate.destination_coordinate_system
        arcpy.env.geographicTransformations = crate.geographic_transformation

        arcpy.CopyFeatures_management(crate.source, crate.destination)

        #: prevent the stepping on of toes in any other scripts
        arcpy.env.outputCoordinateSystem = None
        arcpy.env.geographicTransformations = None
    # add hash fields to destination data
    _add_hash_fields(crate)


def _add_hash_fields(crate):
    arcpy.AddField_management(crate.destination, attribute_hash_field, 'TEXT', field_length=32)
    arcpy.AddField_management(crate.destination, geometry_hash_field, 'TEXT', field_length=32)


def _is_table(crate):
    '''
    crate: Crate

    returns True if the crate defines a table
    '''
    return arcpy.Describe(crate.source).datasetType == 'Table'


def _create_geo_hash(wkt, orderNum):
    hasher = md5(wkt)
    hasher.update(str(orderNum))
    return hasher.hexdigest()


def _get_hash_lookups(dest):
    hashLookup = {}
    geoHashLookup = {}
    attHashColumn = attribute_hash_field
    geoHashColumn = geometry_hash_field
    with arcpy.da.SearchCursor(dest, ['OID@', attHashColumn, geoHashColumn]) as cursor:
        for row in cursor:
            oid, attHash, geoHash = row
            if attHash is not None:
                hashLookup[str(attHash)] = 0
            if geoHash is not None:
                geoHashLookup[str(geoHash)] = 0
    return (hashLookup, geoHashLookup)


def _move_data(crate):
    '''
    crate: Crate

    move data from source to destination as defined by the crate
    '''
    shape_token = 'SHAPE@'
    attHashColumn = attribute_hash_field
    geoHashColumn = geometry_hash_field
    is_table = _is_table(crate)

    log.info('checking for changes...')
    fields = set([fld.name for fld in arcpy.ListFields(crate.destination)]) & set([fld.name for fld in arcpy.ListFields(crate.source)])
    fields = _filter_fields(fields)
    fields.sort()

    attHashSubIndex = None
    if 'OID@' in fields:
        fields.remove('OID@')
        fields.append('OID@')
        attHashSubIndex = -1

    source = crate.source
    if not is_table:
        fields.append(shape_token)
        attHashSubIndex = -2
        if arcpy.Describe(crate.source).spatialReference.name != arcpy.Describe(crate.destination).spatialReference.name:
            temp_table = crate.destination + reproject_temp_suffix
            #: data may have already been projected in has_changes
            if not arcpy.Exists(temp_table):
                log.debug('creating %s', temp_table)
                arcpy.CopyFeatures_management(crate.source, temp_table)

            source = temp_table

    sql_clause = None
    objectIdField = 'OBJECTID'  # arcpy.Describe(source).OIDFieldName
    if objectIdField in [f.name for f in arcpy.ListFields(crate.source)]:
        sql_clause = (None, 'ORDER BY {}'.format(objectIdField))

    try:
        newRows = []
        hashLookup, geoHashLookup = _get_hash_lookups(crate.destination)
        orderNum = 0
        atthashCount = 0
        with arcpy.da.SearchCursor(source, fields, sql_clause=sql_clause) as srcCursor:
            for row in srcCursor:
                orderNum += 1
                # Shape hash
                geoHexDigest = None
                if not is_table:
                    wkt = row[-1].WKT
                    geoHexDigest = _create_geo_hash(wkt, orderNum)
                # Attribute hash
                hasher = md5()
                hs = str(row[:attHashSubIndex]) + str(orderNum)
                hasher.update(hs)
                attHexDigest = hasher.hexdigest()
                # Check for new feature
                if attHexDigest not in hashLookup:
                    listRow = list(row)
                    listRow.extend([geoHexDigest, attHexDigest])
                    newRows.append(listRow)
                    atthashCount += 1
                elif geoHexDigest not in geoHashLookup:
                    listRow = list(row)
                    listRow.extend([geoHexDigest, attHexDigest])
                    newRows.append(listRow)
                else:  # TODO: make specific to each hash or just use one
                    hashLookup[attHexDigest] = 1
                    geoHashLookup[geoHexDigest] = 1
        # Find hashes from hashLookup that were never accessed
        oldGeoHashes = [h for h in geoHashLookup if geoHashLookup[h] == 0]
        oldHashes = [h for h in hashLookup if hashLookup[h] == 0]
        oldGeoHashCount = len(oldGeoHashes)
        oldHashCount = len(oldHashes)
        newRowCount = len(newRows)
        if oldGeoHashCount + oldHashCount + newRowCount > 0:
            log.info('updating data...')
            # edit session required for data that participates in relationships
            log.debug('starting edit session...')
            edit_session = arcpy.da.Editor(crate.destination_workspace)
            edit_session.startEditing(False, False)
            edit_session.startOperation()

            if oldGeoHashCount > 0 or oldHashCount > 0:
                whereSelection = """{} IN ('{}')""".format(attHashColumn,
                                                           "','".join(oldHashes))
                log.debug('removed rows: {}'.format(oldHashCount))
                with arcpy.da.UpdateCursor(crate.destination, [attHashColumn], whereSelection) as uCursor:
                    for row in uCursor:
                        uCursor.deleteRow()

            if newRowCount > 0:
                fields.extend([geoHashColumn, attHashColumn])
                log.debug('inserted rows: {}'.format(newRowCount))
                with arcpy.da.InsertCursor(crate.destination, fields) as iCursor:
                    for row in newRows:
                        iCursor.insertRow(row)

            edit_session.stopOperation()
            edit_session.stopEditing(True)
            log.debug('edit session stopped')
        else:
            log.info('no changes found')
    except:
        log.warn('Error while trying to update data via InsertCursor. Falling back to Append tool...', exc_info=True)

        edit_session.stopOperation()
        edit_session.stopEditing(False)
        log.debug('edit session stopped without saving changes')
        log.debug('truncating data for %s', crate.destination_name)
        arcpy.TruncateTable_management(crate.destination)
        arcpy.Append_management(source, crate.destination, 'NO_TEST')


def check_schema(crate):
    '''
    crate: Crate

    returns: Boolean - True if the schemas match, raises ValidationException if no match
    '''

    def get_fields(dataset):
        field_dict = {}

        for field in arcpy.ListFields(dataset):
            #: don't worry about comparing OBJECTID field
            if not _is_naughty_field(field.name) and field.name != 'OBJECTID' and field.name != attribute_hash_field and field.name != geometry_hash_field:
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


def _filter_fields(lst):
    '''
    lst: String[]

    returns: String[]

    Filters out fields that mess up the update logic.
    '''

    new_fields = []
    for fld in lst:
        if fld == 'OBJECTID':
            new_fields.insert(0, 'OID@')
        elif not _is_naughty_field(fld):
            new_fields.append(fld)

    return new_fields


def _is_naughty_field(fld):
    return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID'] or fld.startswith('OBJECTID_')


def _has_changes(crate):
    '''
    crate: Crate

    returns: Boolean
        False if there are no changes
    '''
    log.info('checking for changes...')

    is_table = _is_table(crate)

    # try simple feature count first
    destination_feature_count = int(arcpy.GetCount_management(crate.destination).getOutput(0))
    source_feature_count = int(arcpy.GetCount_management(crate.source).getOutput(0))

    log.debug('destination feature count: %s source feature count: %s', destination_feature_count, source_feature_count)
    if destination_feature_count != source_feature_count:
        log.info('feature count is different. source: %d destination: %d', source_feature_count, destination_feature_count)
        return True

    fields = set([fld.name for fld in arcpy.ListFields(crate.destination)]) & set([fld.name for fld in arcpy.ListFields(crate.source)])

    # filter out shape fields and other problematic fields
    fields = _filter_fields(fields)

    def is_almost_equal(arg, arg2):
        difference = fabs(arg - arg2)

        return difference <= 10.0

    temp_compare_table = None

    if not is_table:
        destination_describe = arcpy.Describe(crate.destination)
        shape_type = destination_describe.shapeType

        if shape_type == 'Polygon':
            shape_token = 'SHAPE@AREA'
        elif shape_type == 'Polyline':
            shape_token = 'SHAPE@LENGTH'
        elif shape_type == 'Point':
            shape_token = 'SHAPE@XY'
        else:
            shape_token = 'SHAPE@JSON'

        fields.append(shape_token)

        def parse_shape(shape_value):
            if shape_value is None:
                return 0
            elif shape_type in ['Polygon', 'Polyline']:
                return shape_value
            elif shape_type == 'Point':
                if shape_value[0] is not None and shape_value[1] is not None:
                    return shape_value[0] + shape_value[1]
                else:
                    return 0
            else:
                return shape_value

        #: support for reprojecting
        if arcpy.Describe(crate.source).spatialReference.name != destination_describe.spatialReference.name:
            temp_compare_table = crate.destination + reproject_temp_suffix

            log.debug('creating %s', temp_compare_table)
            arcpy.Project_management(crate.source, temp_compare_table, destination_describe.spatialReference, crate.geographic_transformation)

    if 'OBJECTID' in [f.name for f in arcpy.ListFields(crate.source)] and 'OBJECTID' in [f.name for f in arcpy.ListFields(crate.destination)]:
        #: compare each feature based on sorting by OBJECTID if both tables have that field
        sql_clause = (None, 'ORDER BY OBJECTID')
    else:
        sql_clause = None

    with arcpy.da.SearchCursor(crate.destination, fields, sql_clause=sql_clause) as f_cursor, \
            arcpy.da.SearchCursor(temp_compare_table or crate.source, fields, sql_clause=sql_clause) as sde_cursor:
        for destination_row, source_row in izip(f_cursor, sde_cursor):
            if destination_row != source_row:
                # check shapes first
                if destination_row[-1] != source_row[-1] and not is_table:
                    if shape_type not in ['Polygon', 'Polyline', 'Point']:
                        #: for complex types always return true for now
                        log.info('complex type = always changes for now')

                        return True

                    destination_shape = parse_shape(destination_row[-1])
                    source_shape = parse_shape(source_row[-1])

                    if is_almost_equal(destination_shape, source_shape):
                        # trim off shapes
                        destination_row = list(destination_row[:-1])
                        source_row = list(source_row[:-1])
                    else:
                        log.info('changes found in a shape comparison')
                        log.debug('\nsource row: %s\ndest   row: %s', source_row, destination_row)

                        return True

                # trim microseconds since they can be off by one between file and sde databases
                for i in range(len(destination_row)):
                    if type(destination_row[i]) is datetime:
                        destination_row = list(destination_row)
                        source_row = list(source_row)
                        destination_row[i] = destination_row[i].replace(microsecond=0)
                        try:
                            source_row[i] = source_row[i].replace(microsecond=0)
                        except:
                            pass

                if fields[0] == 'OID@':
                    # compare all values except OBJECTID
                    start_field_index = 1
                else:
                    start_field_index = 0

                if destination_row[start_field_index:] != source_row[start_field_index:]:
                    log.info('changes found in non-shape field comparison')
                    log.debug('source row: %s, destination row: %s', source_row[start_field_index:], destination_row[start_field_index:])

                    return True

    log.info('no changes found')

    return False


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
