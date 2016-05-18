#!/usr/bin/env python
# * coding: utf8 *
'''
test_plugin.py

A module that contains tests for the plugin module.
'''

import unittest
from forklift.plugin import ScheduledUpdateBase
from nose.tools import raises


class Plugin(ScheduledUpdateBase):
    '''a test class for how plugins should work
    '''

    def nightly(self):
        pass


class BadPlugin(ScheduledUpdateBase):
    '''a test class for how plugins should work
    '''


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.patient = Plugin()

    @raises(NotImplementedError)
    def test_no_nightly_raises_exception(self):
        self.patient = BadPlugin()

        self.patient.nightly()

    def test_with_nightly(self):
        self.patient = Plugin()

        self.patient.nightly()

    def test_defaults(self):
        self.assertEquals(self.patient.get_dependent_layers(), [])
        self.assertEquals(self.patient.get_source_location(), 'C:\\MapData\\SGID10.sde')
        self.assertEquals(self.patient.get_destination_location(), 'C:\\MapData\\SGID10.gdb')

    def test_can_use_logging(self):
        self.patient.log.info('this works')
