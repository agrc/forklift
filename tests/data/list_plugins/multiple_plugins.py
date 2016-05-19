#!/usr/bin/env python
# * coding: utf8 *
'''
multiple_plugins.py

A module that contains plugins to be used in test_lift.py tests
'''

from forklift.plugin import ScheduledUpdateBase


class PluginOne(ScheduledUpdateBase):

    def __init__(self, arg):
        pass


class PluginTwo(ScheduledUpdateBase):

    def __init__(self, arg):
        pass
