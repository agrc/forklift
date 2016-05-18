#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
arcpy_mock.py
----------------------------------
mock arcpy for testing on travis
'''


class Env(object):

    @property
    def workspace(self):
        pass

    @workspace.setter
    def workspace(self, value):
        pass

env = Env()


def Exists(arg):
    return True
