#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
mocks
----------------------------------
mock arcpy for testing
'''


class Describe(object):

    @property
    def OIDFieldName(self):
        return 'OBJECTID'

    @property
    def hasOID(self):
        return True

    @property
    def fields(self):
        return []

    @property
    def datasetType(self):
        return ''

    @property
    def spatialReference(self):
        return SpatialReference()

    def __init__(self, path):
        pass


class SpatialReference(object):

    @property
    def name(self):
        return ''
