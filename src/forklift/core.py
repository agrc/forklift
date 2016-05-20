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


class Core(object):

    def __init__(self):
        self.log = logging.getLogger(settings.LOGGER)
        self.changes = []

    def update_dataset(self, fgdb, f, sdeFC):
        '''
        fgdb: String - file geodatabase
        f: String - name of feature class to update
        sdeFC: String - path to SDE feature class
        is_table: Boolean
        returns: Boolean - True if update was successful (even if no changes were found)

        Updates f with data from sdeFC.
        '''

        arcpy.env.workspace = fgdb
        is_table = arcpy.Describe(f).datasetType == 'Table'

        try:
            self.log.info('checking for schema changes...')
            if not self.check_schema(f, sdeFC):
                # skip updating if the schemas do not match
                return False

            self.log.info('checking for changes...')
            if self.check_for_changes(f, sdeFC, is_table):
                self.log.info('updating data...')
                self.log.debug('trucating data for %s', f)
                arcpy.TruncateTable_management(f)

                # edit session required for data that participates in relationships
                self.log.debug('starting edit session...')
                editSession = arcpy.da.Editor(fgdb)
                editSession.startEditing(False, False)
                editSession.startOperation()

                fields = [fld.name for fld in arcpy.ListFields(f)]
                fields = self._filter_fields(fields)
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
                self.log.debug('edit session stopped')

                self.changes.append(f.upper())
            else:
                self.log.info('no changes found')

            return True
        except Exception as e:
            self.log.error(e)

            return False

    def check_schema(self, source_dataset, destination_dataset):
        '''
        source_dataset: String
        destination_dataset: String

        returns: Boolean - True if the schemas match
        '''

        def get_fields(dataset):
            field_dict = {}
            for field in arcpy.ListFields(dataset):
                if not self._is_naughty_field(field.name):
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
            self.log.error('Missing fields in %s: %s', source_dataset, ', '.join(missing_fields))
            return False
        elif len(mismatching_fields) > 0:
            self.log.error('Mismatching fields in %s: %s', source_dataset, ', '.join(mismatching_fields))
            return False
        else:
            return True

    def update_fgdb_from_sde(self, fgdb, sde):
        '''
        fgdb: String - file geodatabase
        sde: String - sde geodatabase connection
        returns: String[] - the list of errors

        Loops through the file geodatabase feature classes and looks for
        matches in the SDE database. If there is a match, it does a schema check
        and then updates the data.
        '''

        self.log.info('Updating %s from %s', fgdb, sde)

        # loop through local feature classes
        arcpy.env.workspace = fgdb
        fcs = arcpy.ListFeatureClasses() + arcpy.ListTables()
        totalFcs = len(fcs)
        i = 0
        for f in fcs:
            i = i + 1
            self.log.info('%s of %s | %s', i, totalFcs, f)

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
                self.log.error('no match found in sde for %s', f)
                continue

            self.update_dataset(fgdb, f, sdeFC)

        return (self.changes)

    def was_modified_today(self, fcname):
        '''
        fcname: String

        returns: Boolean

        Checks to see if fcname within the fgdb was updated today.
        '''

        return fcname.upper() in self.changes

    def _filter_fields(self, lst):
        '''
        lst: String[]

        returns: String[]

        Filters out fields that mess up the update logic.
        '''

        newFields = []
        for fld in lst:
            if not self._is_naughty_field(fld):
                newFields.append(fld)
        return newFields

    def _is_naughty_field(self, fld):
        return 'SHAPE' in fld.upper() or fld.upper() in ['GLOBAL_ID', 'GLOBALID']

    def check_for_changes(self, f, sde, is_table):
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
            fields = self._filter_fields(fields)

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
