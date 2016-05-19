#!/usr/bin/env python
# * coding: utf8 *
'''
single_plugin.py

A module that contains plugins to be used in test_lift.py tests
'''

from forklift.plugin import ScheduledUpdateBase


class SinglePlugin(ScheduledUpdateBase):

    def __init__(self, arg):
        pass
