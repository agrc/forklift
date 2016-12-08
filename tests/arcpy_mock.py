#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
arcpy_mock
----------------------------------
mock arcpy for testing on travis
'''


class Describe(object):

    def __init__(self, arg):
        pass

    @property
    def hasOID(self):
        return True

    @property
    def OIDFieldName(self):
        return 'OBJECTID'
