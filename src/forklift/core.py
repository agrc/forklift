#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
core.py
-----------------------------------------
Tools for updating a filegeodatabase from an SDE database
'''

import arcpy
import logging
import settings
from datetime import datetime
from itertools import izip
from numpy.testing import assert_almost_equal
from os.path import join

changes = []
log = logging.getLogger(settings.LOGGER)


def update_fgdb_from_sde(fgdb, sde):
    global changes
    '''
    fgdb: file geodatabase
    sde: sde geodatabase connection
    returns: String[] - the list of errors

    Loops through the file geodatabase feature classes and looks for
    matches in the SDE database. If there is a match, it does a schema check
    and then updates the data.
    '''

    def update_data(is_table):
        try:
            # validate that there was not a schema change
            arcpy.env.workspace = fgdb
            layer = sdeFC + '_Layer'
            if not is_table:
                arcpy.MakeFeatureLayer_management(sdeFC, layer, '1 = 2')
            else:
                arcpy.MakeTableView_management(sdeFC, layer, '1 = 2')

            try:
                arcpy.Append_management(layer, f, 'TEST')
                log.info('schema test passed')
                passed = True
            except arcpy.ExecuteError as e:
                if '000466' in e.message:
                    log.error(e)
                    msg = 'schema change detected'
                    msg += '\n\n{0}'.format(_get_field_differences(sdeFC, f))
                    errors.append('{}: {}'.format(f, msg))
                    log.error(msg)
                    passed = False
                    return passed
                else:
                    raise e
            arcpy.Delete_management(layer)

            log.info('checking for changes...')
            if check_for_changes(f, sdeFC, is_table) and passed:
                log.info('updating data...')
                arcpy.TruncateTable_management(f)

                # edit session required for data that participates in relationships
                editSession = arcpy.da.Editor(fgdb)
                editSession.startEditing(False, False)
                editSession.startOperation()

                fields = [fld.name for fld in arcpy.ListFields(f)]
                fields = _filter_fields(fields)
                if not is_table:
                    fields.append('SHAPE@')
                    outputSR = arcpy.Describe(f).spatialReference
                else:
                    outputSR = None
                with arcpy.da.InsertCursor(f, fields) as icursor, \
                    arcpy.da.SearchCursor(sdeFC, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                                          spatial_reference=outputSR) as cursor:
                    for row in cursor:
                        icursor.insertRow(row)

                editSession.stopOperation()
                editSession.stopEditing(True)

                changes.append(f.upper())
            else:
                log.info('no changes found')
        except:
            errors.append('Error updating: {}'.format(f))

    log.info('Updating %s from %s', fgdb, sde)
    errors = []

    # loop through local feature classes
    arcpy.env.workspace = fgdb
    fcs = arcpy.ListFeatureClasses() + arcpy.ListTables()
    totalFcs = len(fcs)
    i = 0
    for f in fcs:
        i = i + 1
        log.info('%d of %d | %s', i, totalFcs, f)

        found = False

        # search for match in stand-alone feature classes
        arcpy.env.workspace = sde
        matches = arcpy.ListFeatureClasses('*.{}'.format(f)) + arcpy.ListTables('*.{}'.format(f))
        if matches is not None and len(matches) > 0:
            match = matches[0]
            sdeFC = join(sde, match)
            found = True
        else:
            # search in feature datasets
            datasets = arcpy.ListDatasets()
            if len(datasets) > 0:
                # loop through datasets
                for ds in datasets:
                    matches = arcpy.ListFeatureClasses('*.{}'.format(f), None, ds)
                    if matches is not None and len(matches) > 0:
                        match = matches[0]
                        sdeFC = join(sde, match)
                        found = True
                        break
        if not found:
            msg = 'no match found in sde'
            errors.append('{}: {}'.format(f, msg))
            log.warning(msg)
            continue

        update_data(arcpy.Describe(join(fgdb, f)).datasetType == 'Table')

    return (errors, changes)


def was_modified_today(fcname):
    '''
    fcname: String

    returns: Boolean

    Checks to see if fcname within the fgdb was updated today.
    '''
    return fcname.upper() in changes


def _filter_fields(lst):
    '''
    lst: String[]

    returns: String[]

    Filters out fields that mess up the schema check.
    '''

    newFields = []
    for fld in lst:
        if 'SHAPE' not in fld.upper() and fld.upper() not in ['GLOBAL_ID', 'GLOBALID']:
            newFields.append(fld)
    return newFields


def _get_field_differences(ds1, ds2):
    def getFields(ds):
        flds = arcpy.ListFields(ds)
        returnFlds = []
        for f in flds:
            returnFlds.append(f.name)

        returnFlds.sort()
        return returnFlds

    ds1Flds = getFields(ds1)
    ds2Flds = getFields(ds2)

    return '{} Fields: \n{}\n{} Fields: \n{}'.format(ds1, ds1Flds, ds2, ds2Flds)


def check_for_changes(f, sde, is_table):
    '''
    f: String
        The name of the fgdb feature class
    sde: String
        The name of the sde feature class
    is_table: Boolean

    returns: Boolean
        False if there are no changes
    '''

    # try simple feature count first
    fCount = int(arcpy.GetCount_management(f).getOutput(0))
    sdeCount = int(arcpy.GetCount_management(sde).getOutput(0))
    if fCount != sdeCount:
        return True

    fields = [fld.name for fld in arcpy.ListFields(f)]

    # filter out shape fields
    if not is_table:
        fields = _filter_fields(fields)

        d = arcpy.Describe(f)
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
        outputSR = arcpy.Describe(f).spatialReference
    else:
        outputSR = None

    # compare each feature based on sorting by OBJECTID
    with arcpy.da.SearchCursor(f, fields, sql_clause=(None, 'ORDER BY OBJECTID')) as fCursor, \
            arcpy.da.SearchCursor(sde, fields, sql_clause=(None, 'ORDER BY OBJECTID'),
                                  spatial_reference=outputSR) as sdeCursor:
        for fRow, sdeRow in izip(fCursor, sdeCursor):
            if fRow != sdeRow:
                # check shapes first
                if fRow[-1] != sdeRow[-1] and not is_table:
                    if shapeType not in ['Polygon', 'Polyline', 'Point']:
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
