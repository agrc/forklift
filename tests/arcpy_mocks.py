#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
arcpy_mocks
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
