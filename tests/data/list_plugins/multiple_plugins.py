#!/usr/bin/env python
# * coding: utf8 *
'''
multiple_plugins.py

A module that contains plugins to be used in test_lift.py tests
'''

from forklift.plugin import ScheduledUpdateBase


class PluginOne(ScheduledUpdateBase):
    expires_in_hours = 1


class PluginTwo(ScheduledUpdateBase):
    expires_in_hours = 2
    dependencies = ['c', 'd']

    def execute(self):
        print('execute: overridden')
