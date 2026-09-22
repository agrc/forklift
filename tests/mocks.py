#!/usr/bin/env python
"""
mocks
----------------------------------
mock arcpy for testing
"""


class Describe:
    @property
    def OIDFieldName(self):
        return "OBJECTID"

    @property
    def hasOID(self):
        return True

    @property
    def fields(self):
        return []

    @property
    def datasetType(self):
        return ""

    @property
    def spatialReference(self):
        return SpatialReference()

    def __init__(self, path):
        pass


class SpatialReference:
    @property
    def name(self):
        return ""
