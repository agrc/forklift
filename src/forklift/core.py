#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating the data associated with a models.Crate
'''

from os import path

from arcgisscripting import ExecuteError
from xxhash import xxh64

import arcpy

from .config import config_location
from .exceptions import ValidationException
from .models import Changes, Crate

log = None

reproject_temp_suffix = '_fl'

hash_field = 'FORKLIFT_HASH'
hash_field_length = 16

src_id_field = 'src_id' + reproject_temp_suffix

garage = path.dirname(config_location)

_scratch_gdb = 'scratch.gdb'

scratch_gdb_path = path.join(garage, _scratch_gdb)

shape_field_index = -2


def init(logger):
    '''
    logger: object

    Make sure forklift is ready to run. Create or clear out the scratch geodatabase.
    logger is passed in from cli.py (rather than just setting it via `log = logging.getLogger('forklift')`)
    to enable other projects to use this module without colliding with the same logger
    '''
    global log
    log = logger

    #: create gdb if needed
    if arcpy.Exists(scratch_gdb_path):
        log.info('%s exists, deleting', scratch_gdb_path)
        try:
            arcpy.Delete_management(scratch_gdb_path)
        except ExecuteError:
            #: swallow error thrown by Pro 2.0
            pass

    log.info('creating: %s', scratch_gdb_path)
    arcpy.CreateFileGDB_management(garage, _scratch_gdb)

    arcpy.ClearEnvironment('workspace')


def update(crate, validate_crate, change_detection):
    '''
    crate: models.Crate
    validate_crate: models.Pallet.validate_crate
    change_detection: ChangeDetection

    returns: (string, string)
        One of the result string constants from models.Crate and an optional message

    Checks to see if a crate can be updated by using validate_crate (if implemented
    within the pallet) or check_schema otherwise. If the crate is valid it then updates the data.
    '''
    arcpy.env.geographicTransformations = crate.geographic_transformation
    change_status = (Crate.NO_CHANGES, None)

    try:
        if not arcpy.Exists(crate.destination):
            log.debug('%s does not exist. creating', crate.destination)
            _create_destination_data(crate, skip_hash_field=change_detection.has_table(crate.source_name))

            change_status = (Crate.CREATED, None)

        #: check for custom validation logic, otherwise do a default schema check
        try:
            has_custom = validate_crate(crate)
            if has_custom == NotImplemented:
                check_schema(crate)
        except Exception as e:
            log.warning('validation error: %s for crate %r', e, crate, exc_info=True)
            return (Crate.INVALID_DATA, str(e))

        #: use change detection data if it exists for this table
        if change_detection.has_table(crate.source_name):
            if change_detection.has_changed(crate.source_name) or change_status[0] == Crate.CREATED:
                return change_detection.update(crate)
            else:
                return change_status
        else:
            #: create source hash and store
            changes = _hash(crate)

        if changes.has_changes():
            log.debug('starting edit session...')
            with arcpy.da.Editor(crate.destination_workspace):
                #: delete un-accessed hashes
                if changes.has_deletes():
                    log.debug('number of rows to be deleted: %d', len(changes._deletes))
                    status, _ = change_status
                    if status != Crate.CREATED:
                        change_status = (Crate.UPDATED, None)

                    log.debug('deleting from destination table')
                    with arcpy.da.UpdateCursor(crate.destination, hash_field) as cursor:
                        for row in cursor:
                            if row[0] in changes._deletes:
                                cursor.deleteRow()

                #: add new/updated rows
                if changes.has_adds():
                    log.debug('number of rows to be added: %d', len(changes.adds))
                    status, message = change_status
                    if status != Crate.CREATED:
                        change_status = (Crate.UPDATED, None)

                    #: reproject data if source is different than destination
                    if crate.needs_reproject():
                        changes.table = arcpy.Project_management(
                            changes.table, changes.table + reproject_temp_suffix,
                            crate.destination_coordinate_system,
                            crate.geographic_transformation,
                            in_coor_system=crate.source_describe['spatialReference'],
                        )[0]

                    if not crate.is_table():
                        changes.fields[shape_field_index] = changes.fields[shape_field_index].rstrip('WKT')

                    #: cache this so we don't have to call it for every record
                    is_table = crate.is_table()
                    with arcpy.da.SearchCursor(changes.table, changes.fields) as add_cursor,\
                            arcpy.da.InsertCursor(crate.destination, changes.fields) as cursor:
                        for row in add_cursor:
                            #: skip null geometries
                            if not is_table and row[shape_field_index] is None:
                                continue

                            cursor.insertRow(row)

            if changes.has_dups:
                change_status = (Crate.UPDATED_OR_CREATED_WITH_WARNINGS, 'duplicate features detected!')
        else:
            log.debug('no changes found.')

            if changes.has_dups:
                change_status = (Crate.WARNING, 'duplicate features detected!')

        #: sanity check the row counts between source and destination
        count_status = _check_counts(crate, changes)

        return count_status or change_status
    except Exception as e:
        log.error('unhandled exception: %s for crate %r', str(e), crate, exc_info=True)

        return (Crate.UNHANDLED_EXCEPTION, str(e))
    finally:
        arcpy.ResetEnvironments()
        arcpy.ClearWorkspaceCache_management()


def _hash(crate):
    '''crate: Crate

    returns a Changes model with deltas for the source
    '''
    shape_token = 'SHAPE@WKT'

    log.info('checking for changes...')
    #: finding and filtering common fields between source and destination
    fields = set([fld.name for fld in arcpy.ListFields(crate.destination)]) & set([fld.name for fld in arcpy.ListFields(crate.source)])
    fields = _filter_fields(fields)

    if not crate.is_table():
        fields.append(shape_token)
    fields.append(hash_field)

    changes = Changes(list(fields))

    attribute_hashes = _get_hash_lookups(crate.destination)
    total_rows = 0

    temp_table = path.join(scratch_gdb_path, crate.name)
    if arcpy.Exists(temp_table):
        arcpy.Delete_management(temp_table)

    if not crate.is_table():
        changes.table = arcpy.CreateFeatureclass_management(
            scratch_gdb_path,
            crate.name,
            geometry_type=crate.source_describe['shapeType'].upper(),
            template=crate.source,
            has_m='SAME_AS_TEMPLATE',
            has_z='SAME_AS_TEMPLATE',
            spatial_reference=crate.source_describe['spatialReference']
        )[0]
    else:
        changes.table = arcpy.CreateTable_management(scratch_gdb_path, crate.name)[0]
        _mirror_fields(crate.source, changes.table)

    #: there's a possibility that source has a hash field already, e.g. harvesting ogm data from AGOL
    if hash_field not in [field.name for field in crate.source_describe['fields']]:
        arcpy.management.AddField(changes.table, hash_field, 'TEXT', field_length=hash_field_length)

    has_dups = False
    with arcpy.da.SearchCursor(crate.source, [field for field in fields if field != hash_field]) as cursor, \
            arcpy.da.InsertCursor(changes.table, changes.fields) as insert_cursor:
        for row in cursor:
            total_rows += 1

            if not crate.is_table():
                #: skip features with empty geometry
                if row[-1] is None:
                    log.warning('empty geometry found in %s', row)
                    total_rows -= 1
                    continue

                #: do this in two parts to prevent creating an unnecessary copy of the WKT
                row_hash = xxh64(str(row[:-1]))
                row_hash.update(row[-1])
            else:
                row_hash = xxh64(str(row))

            digest = row_hash.hexdigest()

            #: check for duplicate hashes
            while digest in changes.adds or digest in changes.unchanged:
                has_dups = True
                row_hash.update(digest)
                digest = row_hash.hexdigest()

            #: check for new feature
            if digest not in attribute_hashes:
                #: update or add
                #: insert into temp table
                insert_cursor.insertRow(row + (digest,))
                #: add to adds
                changes.adds[digest] = None
            else:
                #: remove not modified hash from hashes
                attribute_hashes.pop(digest)

                changes.unchanged[digest] = None

    changes.determine_deletes(attribute_hashes)
    changes.total_rows = total_rows

    if has_dups:
        log.warning('duplicate features detected!')
        changes.has_dups = True

    return changes


def _create_destination_data(crate, skip_hash_field=False):
    '''crate: Crate

    Creates the destination workspace (if necessary) and table/feature class.
    '''
    if not path.exists(crate.destination_workspace):
        if crate.destination_workspace.endswith('.gdb'):
            log.warning('destination not found; creating %s', crate.destination_workspace)
            arcpy.CreateFileGDB_management(path.dirname(crate.destination_workspace), path.basename(crate.destination_workspace))
        else:
            raise Exception('destination_workspace does not exist! {}'.format(crate.destination_workspace))

    try:
        source_metadata = arcpy.metadata.Metadata(crate.source)
    except Exception as error:
        log.warning('getting source metadata failed: %s', error)
        source_metadata = None

    if crate.is_table():
        log.warning('creating new table: %s', crate.destination)
        arcpy.CreateTable_management(crate.destination_workspace, crate.destination_name)
        _mirror_fields(crate.source, crate.destination)
    else:
        log.warning('creating new feature class: %s', crate.destination)
        arcpy.CreateFeatureclass_management(
            crate.destination_workspace,
            crate.destination_name,
            geometry_type=crate.source_describe['shapeType'].upper(),
            template=crate.source,
            has_m='SAME_AS_TEMPLATE',
            has_z='SAME_AS_TEMPLATE',
            spatial_reference=crate.destination_coordinate_system or crate.source_describe['spatialReference']
        )

    if source_metadata is not None:
        destination_metadata = arcpy.metadata.Metadata(crate.destination)
        destination_metadata.copy(source_metadata)
        destination_metadata.save()

    if not skip_hash_field:
        arcpy.AddField_management(crate.destination, hash_field, 'TEXT', field_length=hash_field_length)


def _get_hash_lookups(destination):
    '''destination: string - path to destination data

    returns a hash lookup for all attributes including geometries
    '''
    hash_lookup = {}

    with arcpy.da.SearchCursor(destination, [hash_field]) as cursor:
        for att_hash, in cursor:
            if att_hash is not None:
                hash_lookup[str(att_hash)] = None

    return hash_lookup


def check_schema(crate):
    '''crate: Crate

    returns: Boolean - True if the schemas match, raises ValidationException if no match
    '''

    def get_fields(dataset, describe):
        field_dict = {}

        for field in arcpy.ListFields(dataset):
            #: don't worry about comparing managed fields
            if not _is_nonhashable_field(field.name, describe):
                field_dict[field.name] = field

        return field_dict

    def abstract_type(type):
        if type in ['Double', 'Integer', 'Single', 'SmallInteger']:
            return 'Numeric'
        else:
            return type

    log.info('checking schema...')
    missing_fields = []
    mismatching_fields = []
    source_fields = get_fields(crate.source, crate.source_describe)
    destination_fields = get_fields(crate.destination, arcpy.da.Describe(crate.destination))

    for field_key in list(destination_fields.keys()):
        if field_key == hash_field:
            continue
        # make sure that all fields from destination are in source
        # not sure that we care if there are fields in source that are not in destination
        destination_fld = destination_fields[field_key]
        if field_key not in list(source_fields.keys()):
            missing_fields.append(destination_fld.name)
        else:
            source_fld = source_fields[field_key]
            if abstract_type(source_fld.type) != abstract_type(destination_fld.type):
                mismatching_fields.append(
                    '{}: source type of {} does not match destination type of {}'.format(source_fld.name, source_fld.type, destination_fld.type)
                )
            elif source_fld.type == 'String':

                def truncate_field_length(field):
                    if field.length > 4000:
                        log.warning('%s is longer than 4000 characters. Truncation may occur.', field.name)
                        return 4000
                    else:
                        return field.length

                source_fld.length = truncate_field_length(source_fld)
                destination_fld.length = truncate_field_length(destination_fld)
                if source_fld.length != destination_fld.length:
                    mismatching_fields.append(
                        '{}: source length of {} does not match destination length of {}'.format(source_fld.name, source_fld.length, destination_fld.length)
                    )

    if len(missing_fields) > 0:
        msg = 'Missing fields in {}: {}'.format(crate.source, ', '.join(missing_fields))
        log.warning(msg)

        raise ValidationException(msg)
    elif len(mismatching_fields) > 0:
        msg = 'Mismatching fields in {}: {}'.format(crate.source, ', '.join(mismatching_fields))
        log.warning(msg)

        raise ValidationException(msg)
    else:
        return True


def _filter_fields(fields):
    '''fields: String[]

    returns: String[]

    Filters out fields that mess up the update logic.
    '''
    new_fields = [field for field in fields if not _is_nonhashable_field(field)]
    new_fields.sort()

    return new_fields


def _is_nonhashable_field(field, describe=None):
    '''field: String

    returns: Boolean

    determines if field is a field that we want to exclude from hashing
    '''
    skip_fields = [hash_field.lower()]

    if describe is not None:
        for prop in ['shapeFieldName', 'lengthFieldName', 'OIDFieldName']:
            if prop in describe:
                skip_fields.append(describe[prop].lower())
    field = field.lower()
    return 'shape' in field or field in skip_fields or field.startswith('objectid')


def _check_counts(crate, changes):
    '''
    crate: Crate
    changes: Changes

    Validates that the row counts between source and destination are the same (ignoring empty geometries)

    returns: (valid, message)
        valid: Boolean - true if counts match
        message: String - warning message if any
    '''

    destination_rows = int(arcpy.GetCount_management(crate.destination).getOutput(0))
    source_rows = changes.total_rows

    if not source_rows == destination_rows:
        status = Crate.WARNING

        if changes.has_changes():
            status = Crate.UPDATED_OR_CREATED_WITH_WARNINGS

        return (status, 'Source row count ({}) does not match destination count ({})!'.format(source_rows, destination_rows))
    elif destination_rows == 0:
        return (Crate.INVALID_DATA, 'Destination has zero rows!')

    return None


def _mirror_fields(source, destination):
    '''
    source: string - path to table
    destination: string - path to table

    adds all of the fields in source to destination
    '''
    TYPES = {
        'Blob': 'BLOB',
        'Date': 'DATE',
        'Double': 'DOUBLE',
        'Guid': 'GUID',
        'Integer': 'LONG',
        'Single': 'FLOAT',
        'SmallInteger': 'SHORT',
        'String': 'TEXT'
    }

    add_fields = []
    for field in arcpy.da.Describe(source)['fields']:
        if field.type in ['OID', 'GlobalID']:
            continue

        add_fields.append([field.name, TYPES[field.type], field.aliasName, field.length])

    arcpy.management.AddFields(destination, add_fields)
