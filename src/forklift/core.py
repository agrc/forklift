#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating the data associated with a models.Crate
'''

import arcpy
import logging
import settings
from datetime import datetime
from itertools import izip
from numpy.testing import assert_almost_equal
from models import Crate
from exceptions import ValidationException

log = logging.getLogger(settings.LOGGER)


def update(crate, validate_crate):
    '''
    crate: models.Crate
    validate_crate: models.Pallet.validate_crate

    returns: String
        One of the result string constants from models.Crate

    Checks to see if a crate can be updated by using validate_crate (if implemented
    within the pallet) or _check_schema otherwise. If the crate is valid it
    then updates the data.
    '''

    try:
        if not arcpy.Exists(crate.source):
            _try_to_find_data_source_by_name(crate)

        if not arcpy.Exists(crate.destination):
            log.debug('%s does not exist. creating', crate.destination)
            _create_destination_data(crate)

            return (Crate.CREATED, None)

        #: check for custom validation logic, otherwise do a default schema check
        try:
            has_custom = validate_crate(crate)
            if has_custom == NotImplemented:
                _check_schema(crate.source, crate.destination)
        except ValidationException as e:
            log.warn('validation error: %s for crate %r',
                     e.message,
                     crate,
                     exc_info=True)
            return (Crate.INVALID_DATA, e.message)

        if _has_changes(crate):
            _move_data(crate)

            return (Crate.UPDATED, None)
        else:
            return (Crate.NO_CHANGES, None)
    except Exception as e:
        log.error('unhandled exception: %s for crate %r', e.message, crate, exc_info=True)
        return (Crate.UNHANDLED_EXCEPTION, e.message)


def _create_destination_data(crate):
    if _is_table(crate):
        arcpy.CopyRows_management(crate.source, crate.destination)
    else:
        arcpy.env.outputCoordinateSystem = crate.destination_coordinate_system
        arcpy.env.geographicTransformations = crate.geographic_transformation

        arcpy.CopyFeatures_management(crate.source, crate.destination)

        #: prevent the stepping on of toes in any other scripts
        arcpy.env.outputCoordinateSystem = None
        arcpy.env.geographicTransformations = None


def _is_table(crate):
    '''
    crate: Crate

    returns True if the crate defines a table
    '''
    return arcpy.Describe(crate.source).datasetType == 'Table'


def _move_data(crate):
    '''
    crate: Crate

    move data from source to destination as defined by the crate
    '''
    is_table = _is_table(crate)

    log.info('moving data...')
    log.debug('trucating data for %s', crate.destination_name)
    arcpy.TruncateTable_management(crate.destination)

    # edit session required for data that participates in relationships
    log.debug('starting edit session...')
    edit_session = arcpy.da.Editor(crate.destination_workspace)
    edit_session.startEditing(False, False)
    edit_session.startOperation()

    fields = [fld.name for fld in arcpy.ListFields(crate.destination)]
    fields = _filter_fields(fields)

    if is_table:
        output_sr = None
    else:
        fields.append('SHAPE@')
        output_sr = arcpy.Describe(crate.destination).spatialReference

    with arcpy.da.InsertCursor(crate.destination, fields) as icursor, \
        arcpy.da.SearchCursor(crate.source, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                              spatial_reference=output_sr) as cursor:
        for row in cursor:
            icursor.insertRow(row)

    edit_session.stopOperation()
    edit_session.stopEditing(True)
    log.debug('edit session stopped')


def _check_schema(source_dataset, destination_dataset):
    '''
    source_dataset: String
    destination_dataset: String

    returns: Boolean - True if the schemas match
    '''

    def get_fields(dataset):
        field_dict = {}

        for field in arcpy.ListFields(dataset):
            if not _is_naughty_field(field.name):
                field_dict[field.name.upper()] = field

        return field_dict

    missing_fields = []
    mismatching_fields = []
    source_fields = get_fields(source_dataset)
    destination_fields = get_fields(destination_dataset)

    for field_key in destination_fields.keys():
        # make sure that all fields from destination are in source
        # not sure that we care if there are fields in source that are not in destination
        destination_fld = destination_fields[field_key]
        if field_key not in source_fields.keys():
            missing_fields.append(destination_fld.name)
        else:
            source_fld = source_fields[field_key]
            if source_fld.type != destination_fld.type:
                mismatching_fields.append('{}: source type of {} does not match destination type of {}'
                                          .format(source_fld.name, source_fld.type, destination_fld.type))
            elif source_fld.type == 'String' and source_fld.length != destination_fld.length:
                mismatching_fields.append('{}: source length of {} does not match destination length of {}'
                                          .format(source_fld.name, source_fld.length, destination_fld.length))

    if len(missing_fields) > 0:
        log.warn('Missing fields in %s: %s', source_dataset, ', '.join(missing_fields))

        return False
    elif len(mismatching_fields) > 0:
        log.warn('Mismatching fields in %s: %s', source_dataset, ', '.join(mismatching_fields))

        return False
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
        if not _is_naughty_field(fld):
            new_fields.append(fld)

    return new_fields


def _is_naughty_field(fld):
    return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID']


def _has_changes(crate):
    '''
    crate: Crate
    f: String
        The name of the fgdb feature class
    sde: String
        The name of the sde feature class
    is_table: Boolean

    returns: Boolean
        False if there are no changes
    '''
    is_table = _is_table(crate)

    # try simple feature count first
    destination_feature_count = int(arcpy.GetCount_management(crate.destination).getOutput(0))
    source_feature_count = int(arcpy.GetCount_management(crate.source).getOutput(0))

    log.debug('destination feature count: %s source feature count: %s', destination_feature_count, source_feature_count)
    if destination_feature_count != source_feature_count:
        return True

    fields = [fld.name for fld in arcpy.ListFields(crate.destination)]

    # filter out shape fields
    if is_table:
        output_sr = None
    else:
        fields = _filter_fields(fields)
        shape_type = arcpy.Describe(crate.destination).shapeType

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

        # support for reprojecting
        output_sr = arcpy.Describe(crate.destination).spatialReference

    # compare each feature based on sorting by OBJECTID
    with arcpy.da.SearchCursor(crate.destination, fields, sql_clause=(None, 'ORDER BY OBJECTID')) as f_cursor, \
            arcpy.da.SearchCursor(crate.source, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                                  spatial_reference=output_sr) as sde_cursor:
        for destination_row, source_row in izip(f_cursor, sde_cursor):
            if destination_row != source_row:
                # check shapes first
                if destination_row[-1] != source_row[-1] and not is_table:
                    if shape_type not in ['Polygon', 'Polyline', 'Point']:
                        #: for complex types always return true for now
                        return True
                    destination_shape = parse_shape(destination_row[-1])
                    source_shape = parse_shape(source_row[-1])
                    try:
                        assert_almost_equal(destination_shape, source_shape, -1)
                        # trim off shapes
                        destination_row = list(destination_row[:-1])
                        source_row = list(source_row[:-1])
                    except AssertionError:
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

                # compare all values except OBJECTID
                if destination_row[1:] != source_row[1:]:
                    return True

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

        return (True, new_name)

    if len(names) > 1:
        return (False, 'Duplcate names: {}'.format(','.join(names)))
