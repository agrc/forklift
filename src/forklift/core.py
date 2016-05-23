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
        if not arcpy.Exists(crate.destination):
            _create_destination_data(crate)

            return Crate.CREATED

        #: check for custom validation logic, otherwise do a default schema check
        try:
            has_custom = validate_crate(crate)
            if has_custom == NotImplemented:
                _check_schema(crate)
        except ValidationException as e:
            return (Crate.INVALID_DATA, e.message)

        if _check_for_changes(crate):
            _move_data(crate)
            return Crate.UPDATED
        else:
            return Crate.NO_CHANGES
    except Exception as e:
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

    log.info('updating data...')
    log.debug('trucating data for %s', crate.destination_name)
    arcpy.TruncateTable_management(crate.destination)

    # edit session required for data that participates in relationships
    log.debug('starting edit session...')
    editSession = arcpy.da.Editor(crate.destination_workspace)
    editSession.startEditing(False, False)
    editSession.startOperation()

    fields = [fld.name for fld in arcpy.ListFields(crate.destination)]
    fields = _filter_fields(fields)
    if not is_table:
        fields.append('SHAPE@')
        outputSR = arcpy.Describe(crate.destination).spatialReference
    else:
        outputSR = None
    with arcpy.da.InsertCursor(crate.destination, fields) as icursor, \
        arcpy.da.SearchCursor(crate.source, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                              spatial_reference=outputSR) as cursor:
        for row in cursor:
            icursor.insertRow(row)

    editSession.stopOperation()
    editSession.stopEditing(True)
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
                mismatching_fields.append(
                    '{}: source type of {} does not match destination type of {}'
                    .format(source_fld.name,
                            source_fld.type,
                            destination_fld.type))
            elif source_fld.type == 'String' and source_fld.length != destination_fld.length:
                mismatching_fields.append(
                    '{}: source length of {} does not match destination length of {}'
                    .format(source_fld.name,
                            source_fld.length,
                            destination_fld.length))

    if len(missing_fields) > 0:
        log.error('Missing fields in %s: %s', source_dataset, ', '.join(missing_fields))
        return False
    elif len(mismatching_fields) > 0:
        log.error('Mismatching fields in %s: %s', source_dataset, ', '.join(mismatching_fields))
        return False
    else:
        return True


def _filter_fields(lst):
    '''
    lst: String[]

    returns: String[]

    Filters out fields that mess up the update logic.
    '''

    newFields = []
    for fld in lst:
        if not _is_naughty_field(fld):
            newFields.append(fld)
    return newFields


def _is_naughty_field(fld):
    return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID']


def _check_for_changes(crate):
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
    fCount = int(arcpy.GetCount_management(crate.destination).getOutput(0))
    sdeCount = int(arcpy.GetCount_management(crate.source).getOutput(0))
    if fCount != sdeCount:
        return True

    fields = [fld.name for fld in arcpy.ListFields(crate.destination)]

    # filter out shape fields
    if not is_table:
        fields = _filter_fields(fields)

        d = arcpy.Describe(crate.destination)
        shapeType = d.shapeType
        if shapeType == 'Polygon':
            shapeToken = 'SHAPE@AREA'
        elif shapeType == 'Polyline':
            shapeToken = 'SHAPE@LENGTH'
        elif shapeType == 'Point':
            shapeToken = 'SHAPE@XY'
        else:
            shapeToken = 'SHAPE@JSON'
        fields.append(shapeToken)

        def parse_shape(shapeValue):
            if shapeValue is None:
                return 0
            elif shapeType in ['Polygon', 'Polyline']:
                return shapeValue
            elif shapeType == 'Point':
                if shapeValue[0] is not None and shapeValue[1] is not None:
                    return shapeValue[0] + shapeValue[1]
                else:
                    return 0
            else:
                return shapeValue

        # support for reprojecting
        outputSR = arcpy.Describe(crate.destination).spatialReference
    else:
        outputSR = None

    # compare each feature based on sorting by OBJECTID
    with arcpy.da.SearchCursor(crate.destination, fields, sql_clause=(None, 'ORDER BY OBJECTID')) as fCursor, \
            arcpy.da.SearchCursor(crate.source, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                                  spatial_reference=outputSR) as sdeCursor:
        for fRow, sdeRow in izip(fCursor, sdeCursor):
            if fRow != sdeRow:
                # check shapes first
                if fRow[-1] != sdeRow[-1] and not is_table:
                    if shapeType not in ['Polygon', 'Polyline', 'Point']:
                        #: for complex types always return true for now
                        return True
                    fShape = parse_shape(fRow[-1])
                    sdeShape = parse_shape(sdeRow[-1])
                    try:
                        assert_almost_equal(fShape, sdeShape, -1)
                        # trim off shapes
                        fRow = list(fRow[:-1])
                        sdeRow = list(sdeRow[:-1])
                    except AssertionError:
                        return True

                # trim microseconds since they can be off by one between file and sde databases
                for i in range(len(fRow)):
                    if type(fRow[i]) is datetime:
                        fRow = list(fRow)
                        sdeRow = list(sdeRow)
                        fRow[i] = fRow[i].replace(microsecond=0)
                        try:
                            sdeRow[i] = sdeRow[i].replace(microsecond=0)
                        except:
                            pass

                # compare all values except OBJECTID
                if fRow[1:] != sdeRow[1:]:
                    return True

    return False
